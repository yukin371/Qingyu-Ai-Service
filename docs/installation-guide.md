# Qingyu AI Service - 安装指南

## 问题描述

如果启动服务时出现以下错误：
```
ModuleNotFoundError: No module named 'fastapi'
```
说明缺少Python依赖包。

## 解决方案

### 方案1: 使用国内镜像源（推荐）

```bash
# 清华镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或者阿里云镜像源
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 或者豆瓣镜像源
pip install -r requirements.txt -i https://pypi.douban.com/simple
```

### 方案2: 配置永久镜像源

**Windows**:
```bash
# 创建 pip 配置目录
mkdir %USERPROFILE%\pip

# 创建配置文件 %USERPROFILE%\pip\pip.ini
# 内容如下：
```

```ini
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
[install]
trusted-host = pypi.tuna.tsinghua.edu.cn
```

**Linux/Mac**:
```bash
# 创建配置文件
mkdir -p ~/.pip
cat > ~/.pip/pip.conf << EOF
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
[install]
trusted-host = pypi.tuna.tsinghua.edu.cn
EOF
```

配置完成后，正常安装：
```bash
cd qingyu-ai-service
pip install -r requirements.txt
```

### 方案3: 手动安装核心依赖

如果requirements.txt安装失败，可以先只安装核心依赖：

```bash
# 核心依赖（足以运行HTTP API）
pip install fastapi uvicorn pydantic pydantic-settings

# 或者使用镜像源
pip install fastapi uvicorn pydantic pydantic-settings -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 方案4: 禁用代理检查

如果使用了代理，尝试禁用代理或设置环境变量：

```bash
# Windows
set HTTP_PROXY=
set HTTPS_PROXY=

# Linux/Mac
unset HTTP_PROXY
unset HTTPS_PROXY

# 然后安装
pip install -r requirements.txt
```

### 方案5: 使用--trusted-host参数

```bash
pip install -r requirements.txt --trusted-host mirrors.aliyun.com
```

## 验证安装

安装完成后，验证依赖是否正确安装：

```bash
cd qingyu-ai-service
python -c "import fastapi; import uvicorn; import pydantic; print('All dependencies installed!')"
```

如果输出 `All dependencies installed!` 说明安装成功。

## 启动服务

安装成功后，启动服务：

```bash
# 方式1: 使用uvicorn命令
cd qingyu-ai-service
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8001

# 方式2: 使用Python直接运行
cd qingyu-ai-service
python src/main.py
```

服务应该会在 http://localhost:8001 启动。

## 测试API

启动成功后，访问：
- API文档: http://localhost:8001/docs
- 健康检查: http://localhost:8001/api/v1/health

## 常见问题

### Q1: SSL证书错误

```
SSL: CERTIFICATE_VERIFY_FAILED
```

**解决方案**:
```bash
# 临时禁用SSL验证（不推荐生产环境）
pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

### Q2: 连接超时

```
ReadTimeoutError
```

**解决方案**:
```bash
# 增加超时时间
pip install -r requirements.txt --timeout 1000
```

### Q3: 权限错误

```
PermissionError
```

**解决方案**:
```bash
# 使用用户安装
pip install -r requirements.txt --user
```

### Q4: 版本冲突

``ERROR: pip's dependency resolver does not currently take into account...
```

**解决方案**:
```bash
# 忽略版本冲突警告
pip install -r requirements.txt --use-deprecated=legacy-resolver
```

## 最小依赖方案

如果完整安装仍有问题，可以使用最小依赖集（仅用于开发测试）：

```bash
pip install fastapi==0.109.0 uvicorn==0.27.0 pydantic==2.5.3 pydantic-settings==2.1.0
```

这样可以运行HTTP API，但LangChain、向量数据库等功能不可用。

## 下一步

安装成功后，请参考：
- [HTTP API测试指南](http-api-test-guide.md)
- [阶段完成报告](phase1-http-api-implementation-report.md)
