import {
  Component,
  onWillStart,
  useRef,
  onMounted,
  onWillUnmount,
} from "@odoo/owl";
import { loadBundle } from "@web/core/assets";

export class PieChart extends Component {
  setup() {
    this.canvasRef = useRef("chart");
    this.chartInstance = null; // Keep track of the chart instance

    onWillStart(async () => {
      // As requested: loading the bundle here
      await loadBundle("web.chartjs_lib");
    });

    onMounted(() => {
      this.renderChart();
    });

    onWillUnmount(() => {
      // Good practice to cleanup Chart instance when component is destroyed
      if (this.chartInstance) {
        this.chartInstance.destroy();
      }
    });
  }

  renderChart() {
    if (!this.canvasRef.el) return;

    // props.data is expected to be: {'m': 10, 's': 20, 'xl': 5}
    const labels = Object.keys(this.props.data).map((l) => l.toUpperCase());
    const data = Object.values(this.props.data);

    const config = {
      type: "pie",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Orders by Size",
            data: data,
            backgroundColor: [
              "#FF6384", // Red
              "#36A2EB", // Blue
              "#FFCE56", // Yellow
              "#4BC0C0", // Teal
              "#9966FF", // Purple
            ],
            hoverOffset: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false, // Important for fitting in cards
        plugins: {
          legend: {
            position: "top",
          },
        },
      },
    };

    const ctx = this.canvasRef.el.getContext("2d");
    this.chartInstance = new Chart(ctx, config);
  }
}

PieChart.template = "awesome_dashboard.piechart";
PieChart.props = {
  data: { type: Object }, // Explicit prop validation
};
