# SUSTechPOINTS

一个基于 Web 的 3D 点云标注工具，适合自动驾驶相关数据集的 3D box 标注、浏览和校验。项目以前端原生 JavaScript + Three.js 为主，后端使用 Python + CherryPy/uWSGI 提供数据读取与保存接口。

![Main UI](./doc/main-ui.png)

## 项目特点

- 支持 LiDAR 点云的 3D 框标注与编辑
- 支持多相机图像联动和标注投影查看
- 支持批量编辑、半自动标注与旋转预测
- 支持通过 URL 直接打开指定数据集和帧
- 提供标签检查、格式转换、可视化等辅助脚本

## 目录概览

```text
.
├── main.py             # Web 服务入口
├── scene_reader.py     # 数据集与标注读取逻辑
├── public/             # 前端静态资源与交互逻辑
├── algos/              # 自动标注/轨迹/旋转相关算法
├── tools/              # 校验、转换、可视化脚本
├── data/               # 数据集目录（仓库内附带示例）
└── Docker/             # 容器化启动配置
```

## 快速开始

### 方式一：直接运行

要求：

- Python 3.10
- 依赖见 `requirement.txt`

安装并启动：

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirement.txt uwsgi
python main.py
```

默认地址：

```text
http://127.0.0.1:8081/
```

可以直接打开示例数据：

```text
http://127.0.0.1:8081/?dataset=example
http://127.0.0.1:8081/?dataset=example&frame=000950
```

### 方式二：Docker

```bash
docker build -t sustechpoints .
docker run --rm -p 8092:8092 -v "$(pwd)/data:/app/data" sustechpoints
```

默认地址：

```text
http://127.0.0.1:8092/
```

## 数据组织

项目默认从 `data/` 目录读取场景数据。一个最小场景通常类似这样：

```text
data/<scene>/
├── lidar/             # 点云帧，如 000950.pcd
├── label/             # 标注结果，如 000950.json
├── camera/<name>/     # 相机图像（可选）
├── calib/camera/      # 相机标定（可选）
├── radar/             # 雷达数据（可选）
└── ego_pose/          # 自车位姿（可选）
```

仓库内已包含 `data/example` 可用于快速验证。

## 常用脚本

- [`tools/check_labels.py`](./tools/check_labels.py)：检查单个场景下的标签一致性
- [`tools/stat.py`](./tools/stat.py)：统计数据集中各类目标数量
- [`tools/trans_label_format.py`](./tools/trans_label_format.py)：转换外部标签格式
- [`tools/visualize-camera.py`](./tools/visualize-camera.py)：将 3D 标注投影到相机图像做可视化

这些脚本的输入路径和参数形式并不完全统一，使用前建议先查看源码。

## 更多文档

- 中文操作说明：[`README_cn.md`](./README_cn.md)
- 标注规范与指南：[`README_guide.md`](./README_guide.md)

