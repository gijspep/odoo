import { Component, useState, useRef, onMounted } from "@odoo/owl";

export class TodoItem extends Component {
  static template = "awesome_owl.todo_item";
  static props = {
    id: { type: Number },
    description: { type: String },
    isCompleted: { type: Boolean },
    onToggle: { type: Function, optional: true },
    onRemove: { type: Function, optional: true },
  };

  toggleCompleted() {
    if (this.props.onToggle) {
      this.props.onToggle();
    }
  }

  remove() {
    if (this.props.onRemove) {
      this.props.onRemove();
    }
  }
}

export class TodoList extends Component {
  static template = "awesome_owl.todo_list";
  static components = { TodoItem };
  setup() {
    const initialTodos = [
      { id: 0, description: "perform odoo", isCompleted: true },
      { id: 1, description: "learn OWL", isCompleted: false },
      { id: 2, description: "buy milk", isCompleted: false },
      { id: 3, description: "purchase egss", isCompleted: false },
      { id: 4, description: "acquire beans", isCompleted: false },
    ];
    this.myRef = useRef("todo_list_input");
    onMounted(() => {
      this.myRef.el.focus();
    });
    this.state = useState({
      todos: initialTodos,
      nextId: initialTodos.length,
    });
  }

  removeTodo(todoId) {
    this.state.todos = this.state.todos.filter((t) => t.id !== todoId);
  }

  toggleTodo(todoId) {
    const todo = this.state.todos.find((t) => t.id === todoId);
    if (todo) {
      todo.isCompleted = !todo.isCompleted;
    }
  }

  addToTodoList(ev) {
    if (ev.key === "Enter" && ev.target.value.trim() !== "") {
      this.state.todos.push({
        id: ++this.state.nextId,
        description: ev.target.value.trim(),
        isCompleted: false,
      });

      ev.target.value = "";
    }
  }
}
