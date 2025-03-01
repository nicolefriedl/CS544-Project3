import grpc
import table_pb2
import table_pb2_grpc
import os
import pandas as pd
import pyarrow.parquet as pq
import threading
from concurrent import futures

UPLOAD_CSV_DIR = "/inputs"
UPLOAD_PARQUET_DIR = "/parquets"

os.makedirs(UPLOAD_CSV_DIR, exist_ok=True)
os.makedirs(UPLOAD_PARQUET_DIR, exist_ok=True)

uploaded_files = {}  
lock = threading.Lock()
condition = threading.Condition(lock)  

class TableServicer(table_pb2_grpc.TableServicer):   
    def Upload(self, request, context):
        print("Received Upload request")

        file_id = len(uploaded_files) + 1
        csv_filename = f"{UPLOAD_CSV_DIR}/file_{file_id}.csv"
        parquet_filename = f"{UPLOAD_PARQUET_DIR}/file_{file_id}.parquet"

        try:
            with open(csv_filename, "wb") as f:
                f.write(request.csv_data)
            print(f"CSV saved at: {csv_filename}")

            df = pd.read_csv(csv_filename)
            df.to_parquet(parquet_filename, engine="pyarrow")
            print(f"Parquet saved at: {parquet_filename}")

            with condition:
                uploaded_files[file_id] = {"csv": csv_filename, "parquet": parquet_filename}
                condition.notify_all()

            return table_pb2.UploadResp(error="")

        except Exception as e:
            print(f"Error processing upload: {e}")
            return table_pb2.UploadResp(error=str(e))

    def ColSum(self, request, context):
        print(f"Received ColSum request for column: {request.column} in format: {request.format}")

        file_format = request.format.lower()
        if file_format not in ["csv", "parquet"]:
            return table_pb2.ColSumResp(error="Invalid format. Use 'csv' or 'parquet'.")

        with condition:
            while not uploaded_files:
                condition.wait()
            file_paths = [file_info[file_format] for file_info in uploaded_files.values()]

        total_sum = 0  

        for file_path in file_paths:
            try:
                if file_format == "csv":
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_parquet(file_path, columns=[request.column])

                if request.column in df.columns:
                    total_sum += df[request.column].sum()

            except Exception as e:
                print(f"Error processing {file_path}: {e}")

        return table_pb2.ColSumResp(total=int(total_sum), error="")

def serve():
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=8),  
        options=[("grpc.so_reuseport", 0)]
    )
    table_pb2_grpc.add_TableServicer_to_server(TableServicer(), server)
    server.add_insecure_port("0.0.0.0:5440")  
    print("Server started on port 5440...")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()