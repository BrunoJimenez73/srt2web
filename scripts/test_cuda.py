import os
import sys
import subprocess

# Get nvidia DLL paths
nvidia_base = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Python', 'pythoncore-3.14-64', 'Lib', 'site-packages', 'nvidia')
paths_to_add = []
for pkg in ['cublas', 'cudnn']:
    bin_path = os.path.join(nvidia_base, pkg, 'bin')
    if os.path.exists(bin_path):
        paths_to_add.append(bin_path)
        print(f'Found: {bin_path}')

# Test DLLs with explicit path
import ctypes
for pkg in ['cublas', 'cudnn']:
    bin_path = os.path.join(nvidia_base, pkg, 'bin')
    if os.path.exists(bin_path):
        for dll_file in os.listdir(bin_path):
            if dll_file.endswith('.dll'):
                try:
                    ctypes.windll.LoadLibrary(os.path.join(bin_path, dll_file))
                    print(f'{dll_file}: OK')
                except Exception as e:
                    print(f'{dll_file}: FAIL - {e}')

# Test ONNX with correct PATH
new_path = os.pathsep.join(paths_to_add) + os.pathsep + os.environ.get('PATH', '')
env = os.environ.copy()
env['PATH'] = new_path

result = subprocess.run([sys.executable, '-c', '''
import os
os.environ["PATH"] = r\"''' + new_path.replace('\\', '\\\\') + '''\"
import onnxruntime as ort
print("CUDA available:", "CUDAExecutionProvider" in ort.get_available_providers())
if "CUDAExecutionProvider" in ort.get_available_providers():
    import numpy as np
    from onnx import helper, TensorProto
    X = helper.make_tensor_value_info("X", TensorProto.FLOAT, [1, 3])
    Y = helper.make_tensor_value_info("Y", TensorProto.FLOAT, [1, 3])
    Z = helper.make_tensor_value_info("Z", TensorProto.FLOAT, [1, 3])
    node = helper.make_node("Add", ["X", "Y"], ["Z"])
    graph = helper.make_graph([node], "test", [X, Y], [Z])
    model = helper.make_model(graph, ir_version=8)
    session = ort.InferenceSession(model.SerializeToString(), providers=["CUDAExecutionProvider"])
    x = np.array([[1.0, 2.0, 3.0]], dtype=np.float32)
    y = np.array([[4.0, 5.0, 6.0]], dtype=np.float32)
    result = session.run(None, {"X": x, "Y": y})
    print("CUDA inference: OK", result[0])
'''], capture_output=True, text=True, env=env)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[:500])
