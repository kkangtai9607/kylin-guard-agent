# Phase 4：LLM Provider 与 Agent 编排

```text
本次只执行 Phase 4。完成后停止。

实现：

1. LLMProvider 抽象；
2. OpenAI-compatible Provider；
3. Qwen/DeepSeek 通过兼容接口配置；
4. MockLLM；
5. 超时、有限重试和熔断；
6. 结构化 JSON 输出；
7. Pydantic Schema 校验；
8. Intent Router；
9. Complexity Router；
10. Planner；
11. ReAct Runner；
12. Plan-and-Execute；
13. Evidence Manager；
14. Response Composer；
15. 安全护栏与 Agent 的完整调用顺序；
16. LLM 不可用时的规则降级；
17. SSE 任务状态输出。

关键边界：

- 模型只选择已注册 Tool；
- 模型不能生成可执行 Shell；
- 模型不能决定最终风险等级；
- 模型输出必须经过 Schema 和 Policy；
- Tool 输出作为 UNTRUSTED_DATA；
- 不记录或展示隐藏思维过程；
- 只记录计划、证据、风险、动作和公开理由摘要；
- 模型不可用时仍能完成基础只读巡检；
- 不得让 LangChain 等框架成为必要依赖，除非有明确 ADR 和收益。

任务路由：

- 简单查询：单 Tool；
- 中等动态诊断：ReAct；
- 复杂任务：Plan-and-Execute，局部可用 ReAct；
- L3 写计划：只生成建议和审批单，不执行。

测试：

- 合法结构化输出；
- 非法 JSON；
- 幻觉 Tool；
- 多余参数；
- Tool 不存在；
- 只读到写升级；
- LLM 超时；
- LLM 断线；
- Tool 输出注入；
- MockLLM 的可重复任务。

验收：

- 用户可通过 API 创建自然语言任务；
- 简单任务正确调用只读 Tool；
- 复杂任务生成结构化计划；
- 所有计划先经过安全校验；
- 任务状态可实时查看；
- 不显示隐藏思维；
- 测试通过。

完成后更新状态和文档，然后停止。
```
