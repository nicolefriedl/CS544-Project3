FROM python:3.10

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir grpcio grpcio-tools pandas pyarrow
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. table.proto

EXPOSE 5440

CMD ["python3", "server.py"]