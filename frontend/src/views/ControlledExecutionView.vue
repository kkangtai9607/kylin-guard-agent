<template>
  <div class="controlled-page">
    <el-alert v-if="!capabilities.enabled" title="当前不是受控执行模式" description="页面允许查看设计，但所有写操作按钮均已禁用。请勿通过前端尝试提升服务器模式。" type="warning" show-icon />
    <section class="panel">
      <div class="panel-head"><div><h3>受控操作台</h3><p>操作员申请 → dry-run → 独立审批 → 一次性令牌 → 执行 → 验证 → 必要时回滚。</p></div><span class="mode-badge">{{zhStatus(capabilities.mode)}}</span></div>
      <el-tabs v-model="tool">
        <el-tab-pane label="重启白名单服务" name="service_restart" />
        <el-tab-pane label="安全更新配置" name="config_safe_update" />
        <el-tab-pane label="终止托管进程" name="terminate_process" />
      </el-tabs>
      <el-form label-position="top" class="controlled-form">
        <template v-if="tool==='service_restart'"><el-form-item label="白名单服务"><el-select v-model="service"><el-option v-for="item in capabilities.allowed_services" :key="item" :label="item" :value="item" /></el-select></el-form-item></template>
        <template v-if="tool==='config_safe_update'"><el-form-item label="托管配置目标"><el-select v-model="targetId"><el-option v-for="item in capabilities.managed_configs" :key="item.target_id" :label="`${item.target_id}（${item.validator} 校验）`" :value="item.target_id" /></el-select></el-form-item><el-form-item label="新配置内容"><el-input v-model="content" type="textarea" :rows="7" maxlength="1048576" show-word-limit /></el-form-item></template>
        <template v-if="tool==='terminate_process'"><el-form-item label="进程 PID"><el-input-number v-model="pid" :min="2" :max="4194304" /></el-form-item><p class="form-note">仅能生成配置中已声明的 systemd 托管进程候选，并绑定进程启动时钟防止 PID 重用。</p></template>
        <el-button type="warning" :disabled="!capabilities.enabled" :loading="submitting" @click="prepare">执行 dry-run 并申请审批</el-button>
      </el-form>
      <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
      <div v-if="preview" class="dry-run-card"><h4>dry-run 影响摘要</h4><pre>{{JSON.stringify(preview,null,2)}}</pre></div>
    </section>

    <section class="panel">
      <div class="panel-head"><div><h3>我的受控任务</h3><p>批准后由原申请人领取一次性令牌并执行。</p></div><el-button @click="refreshApprovals">刷新审批状态</el-button></div>
      <el-table :data="approvals" empty-text="本页面尚未创建审批申请">
        <el-table-column prop="tool_name" label="工具" width="190" />
        <el-table-column label="参数摘要"><template #default="scope">{{argumentText(scope.row.arguments_summary)}}</template></el-table-column>
        <el-table-column label="状态" width="110"><template #default="scope">{{zhStatus(scope.row.status)}}</template></el-table-column>
        <el-table-column label="操作" width="180"><template #default="scope"><el-button v-if="scope.row.status==='APPROVED'" type="success" size="small" @click="execute(scope.row)">领取令牌并执行</el-button><span v-else-if="scope.row.status==='PENDING'">等待独立审批人</span><span v-else>已处理</span></template></el-table-column>
      </el-table>
    </section>

    <section class="panel">
      <div class="panel-head"><div><h3>执行、验证与回滚记录</h3><p>每次执行均关联审批、备份或状态快照及独立验证结果。</p></div><el-button @click="loadExecutions">刷新记录</el-button></div>
      <el-table :data="executions" empty-text="暂无执行记录">
        <el-table-column prop="tool_name" label="工具" width="180" />
        <el-table-column prop="target_ref" label="目标" />
        <el-table-column label="状态" width="110"><template #default="scope">{{zhStatus(scope.row.status)}}</template></el-table-column>
        <el-table-column prop="backup_status" label="备份/快照" width="140" />
        <el-table-column label="验证"><template #default="scope">{{scope.row.verifications.map((item:Verification)=>`${item.status}: ${item.details}`).join('；')}}</template></el-table-column>
        <el-table-column label="操作" width="130"><template #default="scope"><el-button v-if="scope.row.rollback_available&&capabilities.enabled" type="danger" size="small" @click="requestRollback(scope.row)">申请回滚</el-button><span v-else>—</span></template></el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import{onMounted,reactive,ref}from"vue";import{ElMessage}from"element-plus";import{api,type Task}from"../api";import{zhStatus}from"../status";
interface Capabilities{enabled:boolean;mode:string;allowed_services:string[];managed_configs:{target_id:string;validator:string}[];managed_processes:{process_name:string;service:string}[]}
interface Approval{id:string;task_id:string;tool_name:string;status:string;arguments_summary:Record<string,unknown>}
interface Verification{status:string;details:string}
interface Execution{change_id:string;task_id:string;tool_name:string;target_ref:string|null;status:string;backup_status:string;verifications:Verification[];rollback_available:boolean}
const capabilities=reactive<Capabilities>({enabled:false,mode:"READ_ONLY",allowed_services:[],managed_configs:[],managed_processes:[]});const tool=ref("service_restart"),service=ref("nginx"),targetId=ref("nginx-main"),content=ref(""),pid=ref(2),preview=ref<unknown>(),error=ref(""),submitting=ref(false),approvals=ref<Approval[]>([]),executions=ref<Execution[]>([]),taskIds=ref<string[]>([]);const actionArguments=reactive<Record<string,Record<string,unknown>>>({});
async function loadCapabilities(){Object.assign(capabilities,await api<Capabilities>("/controlled/capabilities"));service.value=capabilities.allowed_services[0]||"";targetId.value=capabilities.managed_configs[0]?.target_id||""}
async function prepare(){submitting.value=true;error.value="";try{const task=await api<Task>("/tasks",{method:"POST",body:JSON.stringify({goal:goalText(),requested_mode:"CONTROLLED_EXECUTION"})});taskIds.value.push(task.id);let args:Record<string,unknown>;if(tool.value==="service_restart")args={service:service.value};else if(tool.value==="config_safe_update")args={target_id:targetId.value,content:content.value};else{const candidate=await api<{candidate_id:string}>("/process-candidates",{method:"POST",body:JSON.stringify({task_id:task.id,pid:pid.value})});args={candidate_id:candidate.candidate_id}}preview.value=await api("/executions/dry-run",{method:"POST",body:JSON.stringify({tool_name:tool.value,arguments:args})});const approval=await api<Approval>(`/tasks/${task.id}/approvals`,{method:"POST",body:JSON.stringify({tool_name:tool.value,arguments:args})});actionArguments[approval.id]=args;ElMessage.success("审批申请已创建，请切换独立审批账号处理");await refreshApprovals()}catch(e){error.value=e instanceof Error?e.message:"受控操作准备失败"}finally{submitting.value=false}}
async function refreshApprovals(){const collected:Approval[]=[];for(const taskId of taskIds.value){collected.push(...await api<Approval[]>(`/tasks/${taskId}/approvals`))}approvals.value=collected}
async function execute(approval:Approval){try{const claimed=await api<{approval_token:string}>(`/approvals/${approval.id}/claim`,{method:"POST"});const args=actionArguments[approval.id]||approval.arguments_summary;await api("/executions/run",{method:"POST",body:JSON.stringify({task_id:approval.task_id,tool_name:approval.tool_name,arguments:args,approval_token:claimed.approval_token})});delete actionArguments[approval.id];ElMessage.success("执行与验证完成");await refreshApprovals();await loadExecutions()}catch(e){error.value=e instanceof Error?e.message:"执行失败"}}
async function requestRollback(execution:Execution){try{const args={change_id:execution.change_id};const approval=await api<Approval>(`/tasks/${execution.task_id}/approvals`,{method:"POST",body:JSON.stringify({tool_name:"rollback_change",arguments:args})});if(!taskIds.value.includes(execution.task_id))taskIds.value.push(execution.task_id);actionArguments[approval.id]=args;ElMessage.success("回滚审批申请已创建");await refreshApprovals()}catch(e){error.value=e instanceof Error?e.message:"回滚申请失败"}}
async function loadExecutions(){executions.value=await api<Execution[]>("/executions")}
function goalText(){if(tool.value==="service_restart")return`重启白名单服务 ${service.value}`;if(tool.value==="config_safe_update")return`安全更新托管配置 ${targetId.value}`;return`终止受控托管进程 PID ${pid.value}`}
function argumentText(value:Record<string,unknown>){return Object.entries(value).map(([key,item])=>`${key}=${item}`).join(" · ")}
onMounted(async()=>{try{await loadCapabilities();await loadExecutions()}catch(e){error.value=e instanceof Error?e.message:"页面加载失败"}});
</script>
