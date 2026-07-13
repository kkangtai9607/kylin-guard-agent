<template>
  <div class="panel">
    <div class="panel-head"><div><h3>L3 人工审批</h3><p>审批人只能批准或拒绝，执行令牌由原申请人另行领取。</p></div><el-button @click="load" :loading="loading">刷新列表</el-button></div>
    <el-alert v-if="error" :title="error" type="error" />
    <el-table :data="rows">
      <el-table-column prop="tool_name" label="受控工具" width="180" />
      <el-table-column label="目标参数"><template #default="scope"><code>{{summary(scope.row.arguments_summary)}}</code></template></el-table-column>
      <el-table-column prop="arguments_hash" label="完整参数哈希" show-overflow-tooltip />
      <el-table-column label="风险" width="90"><template #default="scope"><el-tag type="danger">{{scope.row.risk_level}}</el-tag></template></el-table-column>
      <el-table-column label="状态" width="110"><template #default="scope">{{zhStatus(scope.row.status)}}</template></el-table-column>
      <el-table-column label="审批操作" width="180"><template #default="scope"><template v-if="scope.row.status==='PENDING'"><el-button size="small" type="success" @click="decide(scope.row.id,'approve')">批准</el-button><el-button size="small" type="danger" @click="decide(scope.row.id,'reject')">拒绝</el-button></template><span v-else>已处理</span></template></el-table-column>
    </el-table>
    <el-empty v-if="!loading&&!rows.length" description="暂无待审批任务" />
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { api } from "../api";
import { zhStatus } from "../status";
interface Approval{id:string;tool_name:string;risk_level:string;arguments_hash:string;arguments_summary:Record<string,unknown>;status:string}
const rows=ref<Approval[]>([]),loading=ref(false),error=ref("");
async function load(){loading.value=true;error.value="";try{rows.value=await api<Approval[]>("/approvals")}catch(e){error.value=e instanceof Error?e.message:"审批列表加载失败"}finally{loading.value=false}}
async function decide(id:string,action:"approve"|"reject"){try{const reason=await ElMessageBox.prompt(`确认${action==="approve"?"批准":"拒绝"}此 L3 操作？请输入公开理由。`,"安全二次确认",{confirmButtonText:"确认",cancelButtonText:"取消",inputPattern:/.+/,inputErrorMessage:"必须填写理由",type:action==="approve"?"warning":"error"});await api(`/approvals/${id}/${action}`,{method:"POST",body:JSON.stringify({reason:reason.value})});ElMessage.success("审批决定已写入防篡改审计链");await load()}catch(e){if(e!=="cancel"&&e!=="close")error.value=e instanceof Error?e.message:"审批失败"}}
function summary(value:Record<string,unknown>){return Object.entries(value).map(([key,item])=>`${key}=${item}`).join(" · ")||"无公开参数"}
onMounted(load);
</script>
