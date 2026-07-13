import { createRouter, createWebHistory } from "vue-router";
import ApprovalView from "./views/ApprovalView.vue";
import ConsoleLayout from "./views/ConsoleLayout.vue";
import DashboardView from "./views/DashboardView.vue";
import DemoWorkflowView from "./views/DemoWorkflowView.vue";
import LoginView from "./views/LoginView.vue";
import OperationsView from "./views/OperationsView.vue";
import ResourceView from "./views/ResourceView.vue";
import TaskView from "./views/TaskView.vue";
import ControlledExecutionView from "./views/ControlledExecutionView.vue";

const operations = [
  ["inspections", "安全巡检", "inspections"],
  ["incidents", "故障事件与根因分析", "incidents"],
  ["drift", "配置漂移", "drift"],
  ["knowledge", "知识库", "knowledge"],
  ["audit", "审计日志", "audit"],
  ["settings", "系统设置", "settings"],
];

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: LoginView },
    {
      path: "/",
      component: ConsoleLayout,
      children: [
        { path: "", component: DashboardView, meta: { title: "运维驾驶舱" } },
        { path: "tasks", component: TaskView, meta: { title: "智能运维对话" } },
        { path: "approvals", component: ApprovalView, meta: { title: "安全审批中心" } },
        { path: "controlled", component: ControlledExecutionView, meta: { title: "受控操作台" } },
        { path: "demo", component: DemoWorkflowView, meta: { title: "安全演示闭环" } },
        { path: "timeline", component: ResourceView, meta: { title: "任务时间线", endpoint: "/audit/events" } },
        { path: "mcp", component: ResourceView, meta: { title: "MCP 工具中心", endpoint: "/mcp/tools" } },
        ...operations.map(([path,title,kind])=>({path,component:OperationsView,meta:{title,kind}})),
      ],
    },
  ],
});
router.beforeEach((to)=>{if(to.path!=="/login"&&!localStorage.getItem("kylin-token"))return "/login"});
export default router;
