// Gazebo Classic world plugin: attach / detach two links with a fixed joint.
//
// Why this exists. The Robotiq fingers in this simulation are driven
// kinematically by gazebo_ros2_control (see the note in
// neo_simulation2/components/arm/robotiq_gripper.urdf.xacro for why force
// control is not viable with this model's inertias and timestep). A kinematic
// finger applies no grip force, so a grasped object cannot be held by friction.
// The standard Gazebo Classic answer is to create a fixed joint between the
// gripper and the object once the fingers are on it, and remove it on release.
// That is what gazebo_grasp_plugin and pal-robotics' gazebo_ros_link_attacher
// do; this is the same idea in ~100 lines with a ROS 2 service.
//
// Load it from the world file:
//
//   <plugin name="neo_link_attacher" filename="libneo_link_attacher_plugin.so">
//     <ros><namespace>/link_attacher</namespace></ros>
//   </plugin>
//
// Then:
//
//   ros2 service call /link_attacher/attach neo_link_attacher/srv/Attach \
//     "{model1: mpo_700, link1: ur10wrist_3_link, model2: cube, link2: link}"
//
// Link names are Gazebo names, after sdformat has lumped fixed-joint chains.

#include <cstdio>
#include <map>
#include <memory>
#include <mutex>
#include <string>

#include <gazebo/common/Plugin.hh>
#include <gazebo/physics/physics.hh>
#include <gazebo_ros/node.hpp>
#include <rclcpp/rclcpp.hpp>

#include "neo_link_attacher/srv/attach.hpp"
#include "neo_link_attacher/srv/set_collide_bitmask.hpp"

namespace neo_link_attacher
{

using Attach = neo_link_attacher::srv::Attach;
using SetCollideBitmask = neo_link_attacher::srv::SetCollideBitmask;

class LinkAttacher : public gazebo::WorldPlugin
{
public:
  void Load(gazebo::physics::WorldPtr world, sdf::ElementPtr sdf) override
  {
    world_ = world;
    physics_ = world->Physics();
    node_ = gazebo_ros::Node::Get(sdf);

    attach_srv_ = node_->create_service<Attach>(
      "attach",
      [this](Attach::Request::SharedPtr req, Attach::Response::SharedPtr res) {
        handle(*req, *res, true);
      });
    detach_srv_ = node_->create_service<Attach>(
      "detach",
      [this](Attach::Request::SharedPtr req, Attach::Response::SharedPtr res) {
        handle(*req, *res, false);
      });

    mask_srv_ = node_->create_service<SetCollideBitmask>(
      "set_collide_bitmask",
      [this](SetCollideBitmask::Request::SharedPtr req,
        SetCollideBitmask::Response::SharedPtr res) {
        set_mask(*req, *res);
      });

    RCLCPP_INFO(node_->get_logger(),
      "link attacher ready: %s/attach, %s/detach, %s/set_collide_bitmask",
      node_->get_namespace(), node_->get_namespace(), node_->get_namespace());
  }

private:
  static std::string key(const Attach::Request & r)
  {
    return r.model1 + "/" + r.link1 + "<->" + r.model2 + "/" + r.link2;
  }

  void handle(const Attach::Request & req, Attach::Response & res, bool attach)
  {
    // Gazebo's physics runs on its own thread; the service runs on the ROS
    // executor's. Creating a joint while a step is in progress is what
    // gazebo_ros_link_attacher does too and works in practice, but a world
    // pause around it costs nothing and removes the race entirely.
    std::lock_guard<std::mutex> guard(mutex_);
    const bool was_paused = world_->IsPaused();
    world_->SetPaused(true);
    try {
      res.ok = attach ? do_attach(req, res.message) : do_detach(req, res.message);
    } catch (const std::exception & e) {
      res.ok = false;
      res.message = std::string("exception: ") + e.what();
    }
    world_->SetPaused(was_paused);

    if (res.ok) {
      RCLCPP_INFO(node_->get_logger(), "%s %s", attach ? "attached" : "detached",
        key(req).c_str());
    } else {
      RCLCPP_WARN(node_->get_logger(), "%s failed: %s", attach ? "attach" : "detach",
        res.message.c_str());
    }
  }

  bool lookup(
    const std::string & model_name, const std::string & link_name,
    gazebo::physics::ModelPtr & model, gazebo::physics::LinkPtr & link,
    std::string & why)
  {
    model = world_->ModelByName(model_name);
    if (!model) {
      why = "no model named '" + model_name + "'";
      return false;
    }
    link = model->GetLink(link_name);
    if (!link) {
      why = "model '" + model_name + "' has no link '" + link_name +
        "' (remember sdformat lumps fixed-joint chains; use the Gazebo name)";
      return false;
    }
    return true;
  }

  bool do_attach(const Attach::Request & req, std::string & msg)
  {
    const auto k = key(req);
    if (joints_.count(k)) {
      msg = "already attached: " + k;
      return true;
    }
    gazebo::physics::ModelPtr m1, m2;
    gazebo::physics::LinkPtr l1, l2;
    if (!lookup(req.model1, req.link1, m1, l1, msg)) {return false;}
    if (!lookup(req.model2, req.link2, m2, l2, msg)) {return false;}

    // The joint belongs to model1 (the robot). Zero relative pose: the links
    // are frozen exactly where they are right now, so the object stays where
    // the fingers found it rather than snapping to some canonical offset.
    auto joint = physics_->CreateJoint("fixed", m1);
    joint->SetName("neo_attach_" + req.model2 + "_" + req.link2);
    joint->Attach(l1, l2);
    joint->Load(l1, l2, ignition::math::Pose3d());
    joint->SetModel(m1);
    joint->Init();

    joints_[k] = joint;
    msg = "attached " + k;
    return true;
  }

  bool do_detach(const Attach::Request & req, std::string & msg)
  {
    const auto k = key(req);
    auto it = joints_.find(k);
    if (it == joints_.end()) {
      msg = "not attached: " + k;
      return false;
    }
    it->second->Detach();
    it->second->Fini();
    joints_.erase(it);
    msg = "detached " + k;
    return true;
  }

  // Collision filtering. ODE evaluates
  //     (a->GetSurface()->collideBitmask & b->GetSurface()->collideBitmask) != 0
  // for every candidate pair at contact generation, each step, so changing the
  // mask on a live SurfaceParams takes effect immediately. This is the only
  // practical route in this workspace: sdformat 9's URDF parser does not carry
  // <collide_bitmask> from a <gazebo reference> extension into the collision's
  // <surface>, it drops it at link level where Gazebo ignores it.
  void set_mask(const SetCollideBitmask::Request & req, SetCollideBitmask::Response & res)
  {
    std::lock_guard<std::mutex> guard(mutex_);
    res.collisions_changed = 0;
    auto model = world_->ModelByName(req.model);
    if (!model) {
      res.ok = false;
      res.message = "no model named '" + req.model + "'";
      RCLCPP_WARN(node_->get_logger(), "set_collide_bitmask: %s", res.message.c_str());
      return;
    }
    gazebo::physics::Link_V links;
    if (req.link.empty()) {
      links = model->GetLinks();
    } else {
      auto link = model->GetLink(req.link);
      if (!link) {
        res.ok = false;
        res.message = "model '" + req.model + "' has no link '" + req.link +
          "' (use the Gazebo name; fixed-joint chains are lumped)";
        RCLCPP_WARN(node_->get_logger(), "set_collide_bitmask: %s", res.message.c_str());
        return;
      }
      links.push_back(link);
    }
    for (const auto & link : links) {
      for (const auto & collision : link->GetCollisions()) {
        collision->GetSurface()->collideBitmask = req.bitmask;
        ++res.collisions_changed;
      }
    }
    res.ok = true;
    char buf[160];
    std::snprintf(buf, sizeof buf, "bitmask 0x%04X on %u collision(s) of %s/%s",
      req.bitmask, res.collisions_changed, req.model.c_str(),
      req.link.empty() ? "*" : req.link.c_str());
    res.message = buf;
    RCLCPP_INFO(node_->get_logger(), "%s", buf);
  }

  gazebo::physics::WorldPtr world_;
  gazebo::physics::PhysicsEnginePtr physics_;
  gazebo_ros::Node::SharedPtr node_;
  rclcpp::Service<Attach>::SharedPtr attach_srv_;
  rclcpp::Service<Attach>::SharedPtr detach_srv_;
  rclcpp::Service<SetCollideBitmask>::SharedPtr mask_srv_;
  std::map<std::string, gazebo::physics::JointPtr> joints_;
  std::mutex mutex_;
};

GZ_REGISTER_WORLD_PLUGIN(LinkAttacher)

}  // namespace neo_link_attacher
