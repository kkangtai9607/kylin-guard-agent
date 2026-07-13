<template>
  <div class="task-page">
    <section class="panel task-composer">
      <div class="panel-head">
        <div>
          <h3>智能运维对话</h3>
          <p>模型负责理解与规划，确定性护栏决定工具是否允许调用。</p>
        </div>
        <span class="mode-badge">{{ zhStatus(session.mode) }}</span>
      </div>
      <div class="prompt-examples">
        <button v-for="example in examples" :key="example" type="button" @click="goal=example">
          {{ example }}
        </button>
      </div>
      <el-input
        v-model="goal"
        type="textarea"
        :rows="5"
        maxlength="4000"
        show-word-limit
        placeholder="例如：分析磁盘空间不足的原因，并列出可以安全清理的旧日志，不要自动删除"
        @keydown.ctrl.enter="run"
      />
      <div class="composer-actions">
        <span>Ctrl + Enter 提交 · 默认不会自动执行写操作</span>
        <el-button class="task-primary" type="primary" :loading="loading" :disabled="!goal.trim()" @click="run">
          开始安全诊断
        </el-button>
      </div>
      <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
    </section>

    <template v-if="result && task">
      <section class="result-summary">
        <div class="summary-card"><span>任务状态</span><strong>{{ zhStatus(result.status) }}</strong></div>
        <div class="summary-card"><span>意图</span><strong>{{ intentText(result.plan.intent) }}</strong></div>
        <div class="summary-card"><span>风险等级</span><strong :class="['risk-level',result.plan.risk_level.toLowerCase()]">{{ result.plan.risk_level }}</strong></div>
        <div class="summary-card"><span>证据数量</span><strong>{{ result.normalized_evidence.length }}</strong></div>
      </section>

      <div class="task-columns">
        <section class="panel">
          <div class="panel-head"><div><h3>公开决策链</h3><p>仅展示可审计的理由摘要，不展示模型隐藏思维。</p></div></div>
          <el-timeline class="decision-timeline">
            <el-timeline-item v-for="item in result.decision_chain" :key="item.stage" :type="item.reason_code==='FORBIDDEN_INPUT'?'danger':'primary'">
              <strong>{{ item.stage }}</strong>
              <p>{{ item.summary }}</p>
              <code>{{ item.reason_code }}</code>
            </el-timeline-item>
          </el-timeline>
        </section>

        <section class="panel">
          <div class="panel-head"><div><h3>根因候选 Top 3</h3><p>置信度由规则和证据计算，不由模型任意生成。</p></div></div>
          <div v-if="result.root_causes.length" class="rca-list">
            <article v-for="(cause,index) in result.root_causes" :key="cause.title" class="rca-card">
              <span class="rank">{{ index+1 }}</span>
              <div><strong>{{ causeTitle(cause.title) }}</strong><p>{{ cause.reason_summary }}</p><small>{{ cause.recommended_actions.join('；') }}</small></div>
              <b>{{ Math.round(cause.confidence*100) }}%</b>
            </article>
          </div>
          <el-empty v-else description="当前证据不足以生成根因候选" />
        </section>
      </div>

      <section class="panel candidate-panel">
        <div class="panel-head">
          <div><h3>安全清理候选</h3><p>候选由路径、保留期、文件占用和关键日志规则确定，不能由模型直接指定。</p></div>
          <el-tag :type="session.mode==='CONTROLLED_EXECUTION'?'warning':'info'">{{ session.mode==='CONTROLLED_EXECUTION'?'可申请受控执行':'仅分析，不会删除' }}</el-tag>
        </div>
        <el-table :data="result.cleanup_analysis" empty-text="未发现满足安全规则的清理候选">
          <el-table-column label="判定" width="100"><template #default="scope"><el-tag :type="scope.row.eligible?'success':'danger'">{{scope.row.eligible?'可申请':'已排除'}}</el-tag></template></el-table-column>
          <el-table-column label="文件"><template #default="scope">{{scope.row.candidate?.path||'—'}}</template></el-table-column>
          <el-table-column label="大小" width="130"><template #default="scope">{{formatBytes(scope.row.candidate?.size_bytes)}}</template></el-table-column>
          <el-table-column label="规则结果" min-width="230"><template #default="scope">{{scope.row.reason_codes.map(reasonText).join('；')}}</template></el-table-column>
          <el-table-column label="操作" width="150"><template #default="scope"><el-button v-if="scope.row.eligible&&session.mode==='CONTROLLED_EXECUTION'" type="warning" size="small" @click="requestCleanup(scope.row.candidate)">申请人工审批</el-button><span v-else>无需操作</span></template></el-table-column>
        </el-table>
      </section>

      <section v-if="approvals.length" class="panel">
        <div class="panel-head"><div><h3>本任务审批与执行</h3><p>审批人与申请人必须独立；批准后由原申请人领取一次性令牌。</p></div><el-button @click="loadApprovals">刷新状态</el-button></div>
        <el-table :data="approvals">
          <el-table-column prop="tool_name" label="受控工具" />
          <el-table-column label="目标"><template #default="scope">{{scope.row.arguments_summary.candidate_id||scope.row.arguments_summary.service||scope.row.arguments_summary.target_id||scope.row.arguments_summary.change_id}}</template></el-table-column>
          <el-table-column label="状态" width="110"><template #default="scope">{{zhStatus(scope.row.status)}}</template></el-table-column>
          <el-table-column label="操作" width="160"><template #default="scope"><el-button v-if="scope.row.status==='APPROVED'" type="success" size="small" @click="executeApproved(scope.row)">领取令牌并执行</el-button><span v-else-if="scope.row.status==='PENDING'">等待审批人处理</span><span v-else>已处理</span></template></el-table-column>
        </el-table>
      </section>

      <section class="panel">
        <div class="panel-head"><div><h3>标准化证据</h3><p>所有系统数据均按不可信数据处理并经过脱敏与长度限制。</p></div></div>
        <el-table :data="result.normalized_evidence" max-height="420">
          <el-table-column prop="evidence_type" label="类型" width="110" />
          <el-table-column prop="source" label="数据来源" width="170" />
          <el-table-column prop="title" label="证据" />
          <el-table-column prop="value" label="值" />
          <el-table-column label="异常度" width="100"><template #default="scope">{{Math.round(scope.row.anomaly_score*100)}}%</template></el-table-column>
          <el-table-column prop="trust_label" label="信任标记" width="150" />
        </el-table>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { ElMessage } from "element-plus";
import { api, type Task } from "../api";
import { useSession } from "../stores/session";
import { zhStatus } from "../status";

interface Plan { intent:string;complexity:string;risk_level:string;summary:string }
interface Decision { stage:string;reason_code:string;summary:string }
interface Evidence { evidence_type:string;source:string;title:string;value:string|number|boolean;anomaly_score:number;trust_label:string }
interface RootCause { title:string;confidence:number;reason_summary:string;recommended_actions:string[] }
interface Candidate { candidate_id:string;path:string;size_bytes:number }
interface CleanupDecision { eligible:boolean;reason_codes:string[];candidate:Candidate|null }
interface AgentResult { status:string;plan:Plan;decision_chain:Decision[];normalized_evidence:Evidence[];root_causes:RootCause[];cleanup_analysis:CleanupDecision[] }
interface Approval { id:string;task_id:string;tool_name:string;status:string;arguments_summary:Record<string,string> }
interface Claimed { approval_token:string }

const session=useSession();
const examples=["分析磁盘空间不足的原因，并列出安全清理候选","检查 nginx 服务为什么异常","查找僵尸进程并分析父进程","检查 8080 端口由哪个进程占用"];
const goal=ref("");
const task=ref<Task>();
const result=ref<AgentResult>();
const approvals=ref<Approval[]>([]);
const error=ref("");
const loading=ref(false);

async function run(){
  if(!goal.value.trim())return;
  loading.value=true;error.value="";approvals.value=[];
  try{
    task.value=await api<Task>("/tasks",{method:"POST",body:JSON.stringify({goal:goal.value.trim()})});
    result.value=await api<AgentResult>(`/tasks/${task.value.id}/run`,{method:"POST"});
    await loadApprovals();
  }catch(e){error.value=e instanceof Error?e.message:"任务执行失败"}finally{loading.value=false}
}
async function requestCleanup(candidate:Candidate){
  if(!task.value)return;
  const argumentsValue={candidate_id:candidate.candidate_id};
  try{
    await api("/executions/dry-run",{method:"POST",body:JSON.stringify({tool_name:"safe_log_cleanup",arguments:argumentsValue})});
    await api(`/tasks/${task.value.id}/approvals`,{method:"POST",body:JSON.stringify({tool_name:"safe_log_cleanup",arguments:argumentsValue})});
    ElMessage.success("审批申请已创建，请使用独立审批账号处理");
    await loadApprovals();
  }catch(e){error.value=e instanceof Error?e.message:"审批申请失败"}
}
async function loadApprovals(){if(task.value)approvals.value=await api<Approval[]>(`/tasks/${task.value.id}/approvals`)}
async function executeApproved(approval:Approval){
  if(!task.value)return;
  try{
    const claimed=await api<Claimed>(`/approvals/${approval.id}/claim`,{method:"POST"});
    const argumentsValue=approval.arguments_summary.candidate_id?{candidate_id:approval.arguments_summary.candidate_id}:approval.arguments_summary;
    const execution=await api<{status:string;verification:string}>("/executions/run",{method:"POST",body:JSON.stringify({task_id:task.value.id,tool_name:approval.tool_name,arguments:argumentsValue,approval_token:claimed.approval_token})});
    ElMessage.success(`执行完成：${execution.verification}`);
    await loadApprovals();
  }catch(e){error.value=e instanceof Error?e.message:"受控执行失败"}
}
function formatBytes(value?:number){if(value===undefined)return"—";const units=["B","KB","MB","GB","TB"];let size=value,index=0;while(size>=1024&&index<units.length-1){size/=1024;index++}return`${size.toFixed(index?1:0)} ${units[index]}`}
function intentText(value:string){return({QUERY:"查询",DIAGNOSIS:"故障诊断",INSPECTION:"安全巡检",CHANGE:"受控变更",CLEANUP:"清理分析",RECOVERY:"恢复",FORBIDDEN:"禁止请求"} as Record<string,string>)[value]||value}
function causeTitle(value:string){return({disk_pressure:"磁盘空间压力",high_cpu:"CPU 负载异常",zombie_process:"僵尸进程",service_failure:"服务故障",config_drift:"配置漂移"} as Record<string,string>)[value]||value}
function reasonText(value:string){return({SAFE_CANDIDATE:"满足安全候选规则",FILE_IS_OPEN:"文件正在使用",OPEN_FILE_STATE_UNKNOWN:"无法确认文件占用状态",CRITICAL_OR_DATABASE_LOG:"关键或数据库日志",RETENTION_PERIOD_NOT_MET:"未达到保留期限",FILE_TYPE_NOT_ALLOWED:"文件类型不允许",BELOW_SIZE_THRESHOLD:"未达到清理阈值",PROTECTED_PATH:"受保护路径"} as Record<string,string>)[value]||value}
</script>
