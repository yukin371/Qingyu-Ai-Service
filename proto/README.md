# Protobuf 定义

本目录包含 gRPC 服务的 Protobuf 定义文件。

## 文件列表

- `ai_service.proto` - AI 服务主协议定义

## 生成代码

### Python

```bash
python -m grpc_tools.protoc -I. --python_out=../src/grpc_server --grpc_python_out=../src/grpc_server ai_service.proto
```

### Go

```bash
protoc --go_out=../pkg/grpc --go-grpc_out=../pkg/grpc ai_service.proto
```

## 注意事项

- 修改 proto 文件后，需要重新生成代码
- 生成的 Python 代码放在 `src/grpc_server/`
- 生成的 Go 代码放在 Go 项目的 `pkg/grpc/`

