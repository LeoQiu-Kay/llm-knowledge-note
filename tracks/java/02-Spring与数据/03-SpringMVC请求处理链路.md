---
slug: java-spring-mvc
title: Spring MVC 请求处理链路
---
# Spring MVC 请求处理链路

> **先记住**：Spring MVC 由 DispatcherServlet 统一接收请求，经 HandlerMapping 找到处理器，再由 HandlerAdapter 完成参数解析和方法调用，返回值经过消息转换或视图解析生成响应；拦截器、异常解析器和过滤器分别处在不同层次。

---

## 1. 它在解决什么问题？

Spring MVC 由 DispatcherServlet 统一接收请求，经 HandlerMapping 找到处理器，再由 HandlerAdapter 完成参数解析和方法调用，返回值经过消息转换或视图解析生成响应；拦截器、异常解析器和过滤器分别处在不同层次。

读这一节时，先带着三个问题：

1. **核心对象是什么？** 哪些状态会在处理过程中发生变化？
2. **主链路怎么走？** 一次处理从哪里开始，到哪里才算结束？
3. **边界在哪里？** 数据量、并发或故障出现后，哪一环最先承压？

---

## 2. 先看全貌

![Spring MVC 的上下文层次](./assets/spring_mvc_context.svg)

<p class="diagram-caption">先建立整体位置感：请求进入 Filter 链 → DispatcherServlet 查找 Handler → Interceptor 执行前置逻辑 → 返回值处理、异常解析与响应写回</p>

### 主链路

```text
[请求进入 Filter 链]
    │
    ▼
[DispatcherServlet 查找 Handler]
    │
    ▼
[Interceptor 执行前置逻辑]
    │
    ▼
[参数绑定并调用 Controller]
    │
    ▼
[返回值处理、异常解析与响应写回]
```

先把这条链路记住即可。接下来再逐层拆开每一步为什么这样设计。

---

## 3. 核心机制，逐层拆开

### 前端控制器流程

DispatcherServlet 协调 HandlerMapping、HandlerAdapter、HandlerExceptionResolver 和 ViewResolver。理解链路有助于定位 404、参数绑定、序列化和异常映射问题。

### 参数与返回值解析

HandlerMethodArgumentResolver 把路径、查询、Header、Body 和认证上下文转换为方法参数；HttpMessageConverter 根据媒体类型序列化和反序列化正文。

### Filter、Interceptor 与 Advice

Filter 属于 Servlet 容器层，可覆盖非 MVC 请求；Interceptor 围绕 Handler；ControllerAdvice 适合统一异常和绑定规则。三者职责重叠会造成顺序和重复处理问题。

---

## 4. 用一段实现把概念落地

下面只保留最关键的主干。阅读时，把代码与上一节的流程一一对应：

```java
@RestController
@RequestMapping("/orders")
class OrderController {
    @GetMapping("/{id}")
    OrderView get(@PathVariable long id,
                  @RequestHeader("X-Request-Id") String requestId) {
        return service.find(id, requestId);
    }

    @ExceptionHandler(OrderNotFoundException.class)
    ProblemDetail notFound(OrderNotFoundException e) {
        return ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, e.getMessage());
    }
}
```

### 对照着看

- **从哪里开始**：请求进入 Filter 链
- **关键状态变化**：Interceptor 执行前置逻辑
- **怎样才算完成**：返回值处理、异常解析与响应写回

---

## 5. 怎么选才不容易错

| 关注点 | 怎么理解 | 怎么验证 |
|---|---|---|
| **边界** | 明确容器、代理、Web、事务和数据访问各自负责什么 | 避免把业务规则藏进框架回调 |
| **代理** | 说明哪些调用会穿过代理，哪些会绕过 | 用集成测试覆盖 self-invocation、final 与异常路径 |
| **数据** | 从索引访问路径、事务边界和连接占用解释性能 | 核对执行计划、锁等待与连接池指标 |
| **可替换性** | 抽象应允许测试替身和实现替换 | 避免全局静态访问与过度自动配置 |

没有脱离场景的“最佳方案”。先写清数据规模、读写比例、故障模型和延迟目标，再做选择。

---

## 6. 放进真实系统，还要考虑什么

- 统一响应体有利于客户端，但不要把文件流、健康检查和标准 HTTP 语义强行包装。
- 参数校验应在边界尽早失败，领域不变量仍需在业务层再次保护。
- 大文件和流式响应避免完整读入内存，异步请求也要正确传播安全和日志上下文。

### 上线前检查

- 用集成测试验证代理、事务、MVC 与数据库真实边界。
- 配置提供默认值、校验、版本和回滚，不把环境差异写死。
- 监控连接池、慢 SQL、事务时长、错误分类和请求 Trace。
- 对自动装配和动态 SQL 保留可解释的启动报告与执行计划。

---

## 7. 常见误区与排查

### 容易踩的坑

1. Content-Type 与 Accept 不匹配导致 415 或 406。
2. 全局异常处理器捕获过宽，把系统故障错误映射为业务成功。
3. 请求体被 Filter 提前读取且未包装，Controller 再读取为空。

### 出现问题时，按这个顺序看

1. **还原现场**：确认受影响的请求、数据、时间窗，以及最近是否有发布或流量变化。
2. **沿链路定位**：从“请求进入 Filter 链”一路检查到“返回值处理、异常解析与响应写回”，找出状态第一次偏离预期的位置。
3. **验证修复**：用最小复现、压力测试或故障注入证明问题消失，同时保留回滚方案。

---

## 8. 最后做一次复盘

> **一句话**：Spring MVC 由 DispatcherServlet 统一接收请求，经 HandlerMapping 找到处理器，再由 HandlerAdapter 完成参数解析和方法调用，返回值经过消息转换或视图解析生成响应；拦截器、异常解析器和过滤器分别处在不同层次。
>
> **主链路**：请求进入 Filter 链 → DispatcherServlet 查找 Handler → Interceptor 执行前置逻辑 → 参数绑定并调用 Controller → 返回值处理、异常解析与响应写回
>
> **关键状态**：Interceptor 执行前置逻辑
>
> **最容易踩的坑**：Content-Type 与 Accept 不匹配导致 415 或 406。

---

## 9. 高频追问

### Q1. 请用一分钟说明Spring MVC 请求处理链路的核心目标与工作机制。

Spring MVC 由 DispatcherServlet 统一接收请求，经 HandlerMapping 找到处理器，再由 HandlerAdapter 完成参数解析和方法调用，返回值经过消息转换或视图解析生成响应；拦截器、异常解析器和过滤器分别处在不同层次。

### Q2. 前端控制器流程的核心机制是什么？

DispatcherServlet 协调 HandlerMapping、HandlerAdapter、HandlerExceptionResolver 和 ViewResolver。理解链路有助于定位 404、参数绑定、序列化和异常映射问题。

### Q3. 参数与返回值解析为什么重要，实际如何落地？

HandlerMethodArgumentResolver 把路径、查询、Header、Body 和认证上下文转换为方法参数；HttpMessageConverter 根据媒体类型序列化和反序列化正文。

### Q4. Spring MVC 请求处理链路在工程落地时如何做取舍？

统一响应体有利于客户端，但不要把文件流、健康检查和标准 HTTP 语义强行包装；参数校验应在边界尽早失败，领域不变量仍需在业务层再次保护；大文件和流式响应避免完整读入内存，异步请求也要正确传播安全和日志上下文。

### Q5. Spring MVC 请求处理链路最常见的故障与排查重点是什么？

Content-Type 与 Accept 不匹配导致 415 或 406；全局异常处理器捕获过宽，把系统故障错误映射为业务成功；请求体被 Filter 提前读取且未包装，Controller 再读取为空。排查时应先用指标和日志确认现象，再缩小到线程、资源、依赖或数据边界。
