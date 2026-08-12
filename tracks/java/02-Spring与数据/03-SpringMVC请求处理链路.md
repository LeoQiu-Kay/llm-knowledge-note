---
slug: java-spring-mvc
title: Spring MVC 请求处理链路
---
# Spring MVC 请求处理链路

## 30 秒回答

Spring MVC 由 DispatcherServlet 统一接收请求，经 HandlerMapping 找到处理器，再由 HandlerAdapter 完成参数解析和方法调用，返回值经过消息转换或视图解析生成响应；拦截器、异常解析器和过滤器分别处在不同层次。

## 核心原理

### 前端控制器流程

DispatcherServlet 协调 HandlerMapping、HandlerAdapter、HandlerExceptionResolver 和 ViewResolver。理解链路有助于定位 404、参数绑定、序列化和异常映射问题。

### 参数与返回值解析

HandlerMethodArgumentResolver 把路径、查询、Header、Body 和认证上下文转换为方法参数；HttpMessageConverter 根据媒体类型序列化和反序列化正文。

### Filter、Interceptor 与 Advice

Filter 属于 Servlet 容器层，可覆盖非 MVC 请求；Interceptor 围绕 Handler；ControllerAdvice 适合统一异常和绑定规则。三者职责重叠会造成顺序和重复处理问题。

## 工程权衡

- 统一响应体有利于客户端，但不要把文件流、健康检查和标准 HTTP 语义强行包装。
- 参数校验应在边界尽早失败，领域不变量仍需在业务层再次保护。
- 大文件和流式响应避免完整读入内存，异步请求也要正确传播安全和日志上下文。

## 常见故障

1. Content-Type 与 Accept 不匹配导致 415 或 406。
2. 全局异常处理器捕获过宽，把系统故障错误映射为业务成功。
3. 请求体被 Filter 提前读取且未包装，Controller 再读取为空。

## 面试追问

- 前端控制器流程在高并发或大规模场景下还需要考虑什么？
- 参数与返回值解析在高并发或大规模场景下还需要考虑什么？
- Filter、Interceptor 与 Advice在高并发或大规模场景下还需要考虑什么？
- 如何为Spring MVC 请求处理链路设计压测、监控与回滚方案？
