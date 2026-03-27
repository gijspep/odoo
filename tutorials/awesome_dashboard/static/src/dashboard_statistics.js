/** @odoo-module **/
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { memoize } from "@web/core/utils/functions";

const dashboardService = {
  start(env) {
    // The memoized function now dynamically handles different URLs
    const getCachedStats = memoize((endpoint) => {
      console.log("Fetching from endpoint:", endpoint);
      return rpc(endpoint);
    });

    return {
      getStatistics: (endpoint) => getCachedStats(endpoint),
    };
  },
};

registry.category("services").add("awesome_dashboard.stats", dashboardService);
