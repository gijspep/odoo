import { Component, useState } from "@odoo/owl";

export class Card extends Component {
  static template = "awesome_owl.card";
  static props = {
    title: { type: String },
    slots: { type: Object, optional: true },
  };
  setup() {
    this.state = useState({ isVisible: true });
  }

  close() {
    this.state.isVisible = !this.state.isVisible;
  }
}
