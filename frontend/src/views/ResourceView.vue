<template>
  <div class="panel">
    <div class="panel-head">
      <div>
        <h3>{{ $route.meta.title }}</h3>
        <p>{{ sourceHint }}</p>
      </div>
      <el-button @click="load" :loading="loading">刷新</el-button>
    </div>
    <el-alert v-if="error" :title="error" type="warning" show-icon />
    <el-table v-if="rows.length" :data="rows">
      <el-table-column
        v-for="key in keys"
        :key="key"
        :prop="key"
        :label="labels[key] || key"
        show-overflow-tooltip
      >
        <template #default="scope">{{ format(scope.row[key], key) }}</template>
      </el-table-column>
    </el-table>
    <el-empty v-else-if="!loading && !error" description="当前没有可展示记录" />
    <pre v-if="raw">{{ raw }}</pre>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { api } from "../api";
import { zhStatus } from "../status";

const route = useRoute();
const loading = ref(false);
const error = ref("");
const rows = ref<Record<string, unknown>[]>([]);
const raw = ref("");
const endpoint = computed(() => String(route.meta.endpoint || ""));
const sourceHint = computed(() => {
  if (endpoint.value.includes("audit")) return "数据来源：审计日志与哈希链";
  if (endpoint.value.includes("mcp")) return "数据来源：MCP 工具注册表";
  return "数据来源：麒麟智维盾后端接口";
});

const labels: Record<string, string> = {
  event_id: "事件编号",
  event_type: "事件类型",
  task_id: "任务编号",
  timestamp: "时间",
  actor_id: "操作者",
  source: "数据来源",
  name: "工具名称",
  title_zh: "中文名称",
  risk_level: "风险等级",
  read_only: "读取类工具",
  status: "状态",
  duration_ms: "耗时（毫秒）",
};

const keys = computed(() =>
  rows.value.length
    ? Object.keys(rows.value[0])
        .filter((key) => !["payload", "previous_hash", "current_hash"].includes(key))
        .slice(0, 7)
    : [],
);

function format(value: unknown, key?: string) {
  if (key === "source") return sourceText(value);
  if (typeof value === "boolean") return value ? "是" : "否";
  if (value == null) return "—";
  return zhStatus(value);
}

function sourceText(value: unknown) {
  return (
    {
      system_snapshot: "系统快照",
      disk_usage_scan: "磁盘用量扫描",
      large_file_scan: "大文件扫描",
      process_list: "进程列表",
      service_status: "服务状态",
      journal_query: "服务日志",
      network_socket_list: "监听端口",
      network_config_snapshot: "网络配置",
      security_baseline_scan: "安全基线巡检",
      config_drift_check: "配置漂移检查",
    } as Record<string, string>
  )[String(value)] || String(value ?? "—");
}

async function load() {
  loading.value = true;
  error.value = "";
  rows.value = [];
  raw.value = "";
  try {
    const data = await api<unknown>(endpoint.value);
    if (Array.isArray(data)) rows.value = data as Record<string, unknown>[];
    else raw.value = JSON.stringify(data, null, 2);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载失败";
  } finally {
    loading.value = false;
  }
}

onMounted(load);
watch(endpoint, load);
</script>
