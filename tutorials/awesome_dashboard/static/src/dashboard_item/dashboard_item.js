import { Component, useState } from "@odoo/owl";

export class DashboardItem extends Component {
  static template = "awesome_dashboard.item";
  static props = {
    title: { type: String },
    slots: { type: Object, optional: true },
    size: { type: Number, optional: true },
  };
  static defaultprops = {
    size: 1,
  };
  setup() {
    this.state = useState({ isVisible: true });
  }

  close() {
    this.state.isVisible = !this.state.isVisible;
  }
}
