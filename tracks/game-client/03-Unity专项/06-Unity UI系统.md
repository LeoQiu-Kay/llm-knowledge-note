---
slug: game-unity-ui-system
title: Unity UI 系统与高性能界面
---
# Unity UI 系统与高性能界面

> **优先级**：P0。

## 1. UI 架构

View 负责显示，ViewModel/Presenter 负责转换状态，命令负责交互。战斗状态不应直接依赖 Button 回调，服务端确认后的结果再刷新 UI。窗口栈要定义打开、覆盖、返回、销毁和输入焦点。

## 2. 性能热点

Canvas rebuild、Layout、Graphic Raycaster、Mask、字体图集和频繁 SetActive 都可能造成尖峰。拆分静态/动态 Canvas，减少层级和 Raycast Target，列表做虚拟化，滚动内容按可见区复用。

## 3. 适配与无障碍

锚点、Canvas Scaler、Safe Area、字体回退和手柄导航要在目标分辨率测试。UI 文本、颜色和交互反馈要支持本地化与可访问性，不要用固定像素假设所有屏幕。

### 高频追问

#### Q1. 为什么 UI 拆 Canvas 能减少卡顿？
Canvas 中一个元素变化可能触发整棵批次重建；将高频变化与静态背景拆开，可以缩小 rebuild 范围，但 Canvas 过多也会增加提交，必须用 Profiler 验证。

#### Q2. 如何设计窗口栈？
维护 modal/normal 层级、输入焦点和返回规则；打开时记录 owner，场景卸载或登录态变化时统一关闭，异步加载完成前显示可取消的占位状态。
