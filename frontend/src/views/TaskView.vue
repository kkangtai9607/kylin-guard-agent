<template>
  <div class="task-page">
    <section class="panel task-composer">
      <div class="panel-head">
        <div>
          <h3>智能运维对话</h3>
          <p>先识别意图，再调用固定 MCP 工具采集证据；读操作直接诊断，写操作进入风险确认与执行验证。</p>
        </div>
        <span class="mode-badge">{{ zhStatus(session.mode) }}</span>
      </div>

      <div class="prompt-examples">
        <button v-for="example in examples" :key="example" type="button" @click="goal = example">
          {{ example }}
        </button>
      </div>

      <el-input
        v-model="goal"
        type="textarea"
        :rows="5"
        maxlength="4000"
        show-word-limit
        placeholder="例如：分析磁盘空间不足的原因，并列出安全清理候选。"
        @keydown.ctrl.enter="run"
      />

      <div class="composer-actions">
        <span>Ctrl + Enter 提交 · 涉及删除、重启、修改配置时会先预检查和风险确认</span>
        <el-button class="task-primary" type="primary" :loading="loading" :disabled="!goal.trim()" @click="run">
          开始诊断
        </el-button>
      </div>
      <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
    </section>

    <template v-if="result && task">
      <section class="panel answer-panel" :class="`answer-${result.diagnosis.level}`">
        <div class="panel-head">
          <div>
            <h3>Agent 结论</h3>
            <p>用户问题：{{ task.goal }}</p>
          </div>
          <el-tag :type="tagType(result.diagnosis.level)">{{ levelText(result.diagnosis.level) }}</el-tag>
        </div>
        <h2>{{ result.diagnosis.headline }}</h2>
        <p class="answer-text">{{ result.diagnosis.answer }}</p>
        <div class="answer-grid">
          <div>
            <b>关键发现</b>
            <ul><li v-for="item in result.diagnosis.findings" :key="item">{{ item }}</li></ul>
          </div>
          <div>
            <b>建议动作</b>
            <ul><li v-for="item in result.diagnosis.recommendations" :key="item">{{ item }}</li></ul>
          </div>
        </div>
      </section>

      <section class="result-summary">
        <div class="summary-card"><span>任务状态</span><strong>{{ zhStatus(result.status) }}</strong></div>
        <div class="summary-card"><span>识别意图</span><strong>{{ intentText(result.plan.intent) }}</strong></div>
        <div class="summary-card"><span>风险等级</span><strong :class="['risk-level', result.plan.risk_level.toLowerCase()]">{{ result.plan.risk_level }}</strong></div>
        <div class="summary-card"><span>证据数量</span><strong>{{ result.normalized_evidence.length }}</strong></div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <div>
            <h3>工具调用计划</h3>
            <p>每一步只能调用注册过的 MCP Tool；参数为空表示该工具无需用户参数。</p>
          </div>
        </div>
        <el-table :data="result.plan.steps" empty-text="安全策略已阻断，未生成工具调用计划">
          <el-table-column prop="sequence" label="步骤" width="80" />
          <el-table-column label="工具" width="210">
            <template #default="scope">{{ toolTitle(scope.row.tool_name) }}</template>
          </el-table-column>
          <el-table-column prop="purpose" label="目的" />
          <el-table-column label="参数" min-width="180">
            <template #default="scope">{{ formatArgs(scope.row.arguments) }}</template>
          </el-table-column>
        </el-table>
      </section>

      <section class="panel candidate-panel">
        <div class="panel-head">
          <div>
            <h3>清理候选</h3>
            <p>缓存、临时文件、下载目录安装包等会先列为候选；删除前仍会校验路径、类型、大小、占用状态和快照哈希。</p>
          </div>
          <el-tag :type="session.mode === 'CONTROLLED_EXECUTION' ? 'warning' : 'info'">
            {{ session.mode === "CONTROLLED_EXECUTION" ? "可发起清理" : "已列出候选，删除需确认" }}
          </el-tag>
        </div>

        <el-alert
          v-if="!result.cleanup_analysis.length"
          title="本次没有清理候选"
          description="常见原因：本次不是清理类问题；允许目录没有超过 10 MB 的大文件；文件类型不在允许范围；文件位于保护路径；或文件正在使用。"
          type="info"
          show-icon
          :closable="false"
        />

        <el-table v-else :data="result.cleanup_analysis">
          <el-table-column label="判定" width="120">
            <template #default="scope">
              <el-tag :type="scope.row.eligible ? 'success' : 'danger'">{{ scope.row.eligible ? "可处理" : "已排除" }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="类型" width="170">
            <template #default="scope">{{ candidateType(scope.row.candidate?.classification) }}</template>
          </el-table-column>
          <el-table-column label="文件">
            <template #default="scope">{{ scope.row.candidate?.path || "无候选文件" }}</template>
          </el-table-column>
          <el-table-column label="大小" width="130">
            <template #default="scope">{{ formatBytes(scope.row.candidate?.size_bytes) }}</template>
          </el-table-column>
          <el-table-column label="规则结果" min-width="230">
            <template #default="scope">{{ scope.row.reason_codes.map(reasonText).join("；") }}</template>
          </el-table-column>
          <el-table-column label="详情" width="100">
            <template #default="scope">
              <el-button size="small" @click="openJson('清理候选详情', scope.row)">查看</el-button>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160">
            <template #default="scope">
              <el-button
                size="small"
                type="primary"
                :disabled="session.mode !== 'CONTROLLED_EXECUTION' || !scope.row.eligible"
                @click="requestCleanup(scope.row.candidate)"
              >
                选择并清理
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section v-if="approvals.length" class="panel">
        <div class="panel-head">
          <div>
            <h3>本任务风险确认</h3>
            <p>确认通过后领取一次性令牌执行；令牌绑定任务、工具和参数哈希。</p>
          </div>
        </div>
        <el-table :data="approvals">
          <el-table-column label="工具" width="180">
            <template #default="scope">{{ toolTitle(scope.row.tool_name) }}</template>
          </el-table-column>
          <el-table-column prop="risk_level" label="风险" width="90" />
          <el-table-column label="状态" width="120">
            <template #default="scope">{{ zhStatus(scope.row.status) }}</template>
          </el-table-column>
          <el-table-column label="参数">
            <template #default="scope">{{ formatArgs(scope.row.arguments_summary) }}</template>
          </el-table-column>
          <el-table-column label="执行" width="130">
            <template #default="scope">
              <el-button size="small" type="success" :disabled="scope.row.status !== 'APPROVED'" @click="executeApproved(scope.row)">执行</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <div class="task-columns">
        <section class="panel">
          <div class="panel-head">
            <div>
              <h3>根因候选</h3>
              <p>百分比是证据置信度，不是执行进度；可点击查看关联证据编号。</p>
            </div>
          </div>
          <div v-if="result.root_causes.length" class="rca-list">
            <article v-for="(cause, index) in result.root_causes" :key="cause.title" class="rca-card">
              <span class="rank">{{ index + 1 }}</span>
              <div>
                <strong>{{ causeTitle(cause.title) }}</strong>
                <p>{{ cause.reason_summary }}</p>
                <small>建议：{{ cause.recommended_actions.join("；") }}</small>
                <el-button text type="primary" @click="openJson('根因候选详情', cause)">查看详情</el-button>
              </div>
              <b>{{ Math.round(cause.confidence * 100) }}%</b>
            </article>
          </div>
          <el-empty v-else description="当前证据不足以生成根因候选。" />
        </section>

        <section class="panel">
          <div class="panel-head">
            <div>
              <h3>公开决策链</h3>
              <p>这是可审计结构化链路，不是模型隐藏思维。</p>
            </div>
          </div>
          <el-timeline class="decision-timeline">
            <el-timeline-item v-for="item in result.decision_chain" :key="item.stage" :type="item.reason_code === 'FORBIDDEN_INPUT' ? 'danger' : 'primary'">
              <strong>{{ item.stage }}</strong>
              <p>{{ item.summary }}</p>
              <code>{{ item.reason_code }}</code>
            </el-timeline-item>
          </el-timeline>
        </section>
      </div>

      <section class="panel">
        <div class="panel-head">
          <div>
            <h3>标准化证据</h3>
            <p>Tool 输出按不可信数据处理，经过脱敏、截断和标准化后用于 RCA。</p>
          </div>
        </div>
        <el-table :data="result.normalized_evidence" max-height="420" empty-text="暂无标准化证据">
          <el-table-column label="类型" width="110">
            <template #default="scope">{{ evidenceType(scope.row.evidence_type) }}</template>
          </el-table-column>
          <el-table-column label="数据来源" width="180">
            <template #default="scope">{{ sourceText(scope.row.source) }}</template>
          </el-table-column>
          <el-table-column prop="title" label="证据" />
          <el-table-column prop="value" label="值" />
          <el-table-column label="异常度" width="110">
            <template #default="scope">{{ Math.round(scope.row.anomaly_score * 100) }}%</template>
          </el-table-column>
          <el-table-column label="信任标记" width="160">
            <template #default="scope">{{ scope.row.trust_label === "UNTRUSTED_DATA" ? "不可信外部数据" : scope.row.trust_label }}</template>
          </el-table-column>
          <el-table-column label="详情" width="100">
            <template #default="scope">
              <el-button size="small" @click="openJson('标准化证据详情', scope.row)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section class="panel">
        <div class="panel-head">
          <div>
            <h3>原始工具回执</h3>
            <p>用于审计和排查；日志文本不会改变系统安全规则。</p>
          </div>
        </div>
        <el-table :data="result.evidence" empty-text="未调用工具">
          <el-table-column label="工具" width="210">
            <template #default="scope">{{ toolTitle(scope.row.tool_name) }}</template>
          </el-table-column>
          <el-table-column label="信任标记" width="180">
            <template #default="scope">{{ scope.row.trust_label === "UNTRUSTED_DATA" ? "不可信外部数据" : scope.row.trust_label }}</template>
          </el-table-column>
          <el-table-column label="注入风险" width="110">
            <template #default="scope">
              <el-tag :type="scope.row.injection_suspected ? 'danger' : 'success'">
                {{ scope.row.injection_suspected ? "疑似" : "未发现" }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="回执" width="100">
            <template #default="scope">
              <el-button size="small" @click="openJson('原始工具回执', scope.row.payload)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </template>

    <el-drawer v-model="detailVisible" :title="detailTitle" size="46%">
      <pre>{{ detailJson }}</pre>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { ElMessage } from "element-plus";
import { api, type Task } from "../api";
import { useSession } from "../stores/session";
import { zhStatus } from "../status";

interface PlanStep { sequence: number; tool_name: string; arguments: Record<string, unknown>; purpose: string }
interface Plan { intent: string; complexity: string; risk_level: string; summary: string; steps: PlanStep[] }
interface Decision { stage: string; reason_code: string; summary: string }
interface Diagnosis { level: string; headline: string; answer: string; findings: string[]; recommendations: string[] }
interface Evidence { evidence_id: string; evidence_type: string; source: string; title: string; value: string | number | boolean; anomaly_score: number; temporal_score: number; trust_label: string; tags: string[] }
interface ToolEvidence { tool_name: string; payload: Record<string, unknown>; trust_label: string; injection_suspected: boolean }
interface RootCause { title: string; confidence: number; evidence_ids: string[]; reason_summary: string; recommended_actions: string[] }
interface Candidate { candidate_id: string; path: string; size_bytes: number; classification?: string }
interface CleanupDecision { eligible: boolean; reason_codes: string[]; candidate: Candidate | null }
interface AgentResult { status: string; summary: string; public_reason: string; diagnosis: Diagnosis; plan: Plan; decision_chain: Decision[]; evidence: ToolEvidence[]; normalized_evidence: Evidence[]; root_causes: RootCause[]; cleanup_analysis: CleanupDecision[] }
interface Approval { id: string; task_id: string; tool_name: string; risk_level: string; status: string; arguments_summary: Record<string, string> }
interface Claimed { approval_token: string }

const session = useSession();
const examples = [
  "分析磁盘空间不足的原因，并列出安全清理候选",
  "查询网络状态",
  "检查 nginx 服务为什么异常",
  "ssh 服务有没有开启",
  "查看 CPU 占用和可疑进程",
  "检查 8080 端口由哪个进程占用",
];
const goal = ref("");
const task = ref<Task>();
const result = ref<AgentResult>();
const approvals = ref<Approval[]>([]);
const error = ref("");
const loading = ref(false);
const detailVisible = ref(false);
const detailTitle = ref("");
const detailJson = ref("");

async function run() {
  if (!goal.value.trim()) return;
  loading.value = true;
  error.value = "";
  approvals.value = [];
  try {
    task.value = await api<Task>("/tasks", { method: "POST", body: JSON.stringify({ goal: goal.value.trim() }) });
    result.value = await api<AgentResult>(`/tasks/${task.value.id}/run`, { method: "POST" });
    await loadApprovals();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "任务执行失败";
  } finally {
    loading.value = false;
  }
}

async function requestCleanup(candidate: Candidate | null) {
  if (!task.value || !candidate) return;
  const argumentsValue = { candidate_id: candidate.candidate_id };
  try {
    await api("/executions/dry-run", { method: "POST", body: JSON.stringify({ tool_name: "safe_log_cleanup", arguments: argumentsValue }) });
    await api(`/tasks/${task.value.id}/approvals`, { method: "POST", body: JSON.stringify({ tool_name: "safe_log_cleanup", arguments: argumentsValue }) });
    ElMessage.success("风险确认已创建，请在风险确认中心处理");
    await loadApprovals();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "清理申请失败";
  }
}

async function loadApprovals() {
  if (task.value) approvals.value = await api<Approval[]>(`/tasks/${task.value.id}/approvals`);
}

async function executeApproved(approval: Approval) {
  if (!task.value) return;
  try {
    const claimed = await api<Claimed>(`/approvals/${approval.id}/claim`, { method: "POST" });
    const argumentsValue = approval.arguments_summary.candidate_id ? { candidate_id: approval.arguments_summary.candidate_id } : approval.arguments_summary;
    const execution = await api<{ status: string; verification: string }>("/executions/run", {
      method: "POST",
      body: JSON.stringify({ task_id: task.value.id, tool_name: approval.tool_name, arguments: argumentsValue, approval_token: claimed.approval_token }),
    });
    ElMessage.success(`执行完成：${execution.verification}`);
    await loadApprovals();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "执行失败";
  }
}

function openJson(title: string, value: unknown) {
  detailTitle.value = title;
  detailJson.value = JSON.stringify(value, null, 2);
  detailVisible.value = true;
}

function formatBytes(value?: number) {
  if (value === undefined) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = value;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(index ? 1 : 0)} ${units[index]}`;
}

function formatArgs(value: Record<string, unknown>) {
  const keys = Object.keys(value || {});
  if (!keys.length) return "无需参数";
  return keys.map((key) => `${key}=${String(value[key])}`).join("；");
}

function tagType(level: string) {
  return level === "critical" ? "danger" : level === "warning" ? "warning" : "success";
}

function levelText(level: string) {
  return ({ ok: "未发现异常", warning: "需要关注", critical: "异常/已阻断" } as Record<string, string>)[level] || level;
}

function intentText(value: string) {
  return ({ QUERY: "查询", DIAGNOSIS: "故障诊断", INSPECTION: "安全巡检", CHANGE: "受控变更", CLEANUP: "清理分析", RECOVERY: "恢复", FORBIDDEN: "禁止请求" } as Record<string, string>)[value] || value;
}

function toolTitle(value: string) {
  return ({
    capability_probe: "能力探测",
    system_snapshot: "系统快照",
    process_list: "进程列表",
    zombie_process_scan: "僵尸进程扫描",
    network_socket_list: "监听端口",
    network_config_snapshot: "网络配置",
    port_owner_lookup: "端口归属",
    disk_usage_scan: "磁盘用量",
    large_file_scan: "大文件扫描",
    open_file_lookup: "文件占用",
    journal_query: "服务日志",
    service_status: "服务状态",
    config_drift_check: "配置漂移",
    io_diagnose: "I/O 诊断",
    security_baseline_scan: "安全基线",
    safe_log_cleanup: "清理候选文件",
  } as Record<string, string>)[value] || value;
}

function causeTitle(value: string) {
  return ({ disk_pressure: "磁盘空间压力", high_cpu: "CPU/进程负载线索", zombie_process: "僵尸进程", service_failure: "服务故障", config_drift: "配置漂移" } as Record<string, string>)[value] || value;
}

function reasonText(value: string) {
  return ({
    SAFE_CANDIDATE: "满足清理候选规则",
    FILE_IS_OPEN: "文件正在使用",
    OPEN_FILE_STATE_UNKNOWN: "无法确认文件占用状态",
    CRITICAL_OR_DATABASE_LOG: "关键或数据库日志/敏感命名",
    RETENTION_PERIOD_NOT_MET: "未达到保留期",
    FILE_TYPE_NOT_ALLOWED: "文件类型不允许",
    BELOW_SIZE_THRESHOLD: "未达到清理阈值",
    PROTECTED_PATH: "受保护路径",
    PATH_REJECTED: "路径不在允许范围",
    STAT_FAILED: "无法读取文件状态",
    NOT_REGULAR_FILE: "不是普通文件",
  } as Record<string, string>)[value] || value;
}

function candidateType(value?: string) {
  return ({ DISPOSABLE_DOWNLOAD_OR_CACHE_CANDIDATE: "下载/临时文件", SAFE_LOG_OR_CACHE_CANDIDATE: "日志/缓存文件" } as Record<string, string>)[String(value)] || "候选文件";
}

function evidenceType(value: string) {
  return ({ metric: "指标", file: "文件", process: "进程", service: "服务", log: "日志", network: "网络", config: "配置" } as Record<string, string>)[value] || value;
}

function sourceText(value: string) {
  return ({
    system_snapshot: "系统快照",
    disk_usage_scan: "磁盘用量扫描",
    large_file_scan: "大文件扫描",
    process_list: "进程列表",
    service_status: "服务状态",
    journal_query: "服务日志",
    network_socket_list: "监听端口",
    network_config_snapshot: "网络配置",
    port_owner_lookup: "端口归属",
  } as Record<string, string>)[value] || value;
}
</script>
