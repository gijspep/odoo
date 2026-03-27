import { Component, useState } from "@odoo/owl";
import { Counter } from "./counter/counter";
import { Card } from "./card/card";
import { TodoList } from "./todo/todo";

export class Playground extends Component {
  static template = "awesome_owl.playground";
  static components = { Counter, Card, TodoList };

  setup() {
    // 1. Create a state for the Playground to hold the total sum
    this.state = useState({
      sum: 0,
    });
  }

  // 2. Create the callback function that the children will trigger
  updateSum(delta) {
    this.state.sum += delta;
  }
}
