# Cách test Neural Equation Finder

## Chạy dashboard

```bash
cd "/Users/ngoleminh/Documents/multi-agent-platform"
./run.sh
```

Mở `http://127.0.0.1:8080`. Trang root sẽ chuyển thẳng tới dashboard duy nhất.

## Test nhanh bằng dữ liệu mẫu

Dashboard mở sẵn dữ liệu bậc hai `y = 0.5x² - 1.2x + 0.7` với 300 dòng.

1. Giữ Target là `target`, Input feature là `x`.
2. Giữ default `32,32`, `tanh`, `lbfgs`, degree `2`.
3. Bấm **Train neural network**.
4. Chờ trạng thái **Complete**.

Kết quả cần thấy: plot có data, neural-network curve và polynomial-surrogate curve; metric có NN test R²/RMSE và Equation fidelity R²; equation dùng alias `x1`, bên dưới ghi `x1 = x`.

Đây là hai câu hỏi khác nhau:

- **NN test R²**: mạng dự đoán target thật trên held-out rows tốt đến đâu.
- **Equation fidelity R²**: phương trình polynomial bắt chước dự đoán của mạng tốt đến đâu.

Fidelity cao không chứng minh đây là định luật vật lý thật.

## Test CSV của bro

CSV cần header và ít nhất 20 rows. Ví dụ:

```csv
temperature,pressure,output
1.0,2.0,5.1
1.2,2.4,6.0
```

Upload file, chọn `output` làm Target, chọn một đến bốn cột input, điều chỉnh model rồi Train. Ô trống/NaN/text trong các cột đã chọn sẽ bị drop và đếm; infinity sẽ bị reject. Cột không được chọn có thể chứa text.

Nếu có một input, plot chính hiển thị curve. Nếu có nhiều input, plot chính chuyển thành Actual vs NN prediction vì không thể ép hàm nhiều chiều lên một trục x duy nhất.

## Hyperparameter thực sự có tác dụng

- Hidden layers: `32,32` nghĩa là hai hidden layer, mỗi layer 32 neurons.
- Activation: `tanh`, `relu`, `logistic`, hoặc `identity`.
- Solver: `lbfgs`, `adam`, hoặc `sgd`. Learning rate bị disable với `lbfgs` vì solver này không dùng nó.
- L2 alpha: regularization strength.
- Max iterations: iteration cap, không phải cam kết model sẽ hội tụ.
- Test fraction: phần dữ liệu giữ lại để đánh giá.
- Equation degree: độ bậc polynomial surrogate.
- Seed: tái lập split và model initialization.

## Test tự động

```bash
.venv/bin/python scripts/test_all.py
```

Browser test cần server đang chạy:

```bash
.venv/bin/python scripts/test_browser.py \
  --base-url http://127.0.0.1:8080 \
  --browser-executable "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --output runs/neural-equation-20261030-01/browser
```

Browser suite upload CSV thật, đổi hyperparameter, train qua subprocess, kiểm tra plot/data/equation, kiểm tra hai session độc lập, chụp desktop 1366×1000 và mobile 390×844, và kiểm tra page không overflow ngang.

## Giới hạn hiện tại

Module này xử lý scalar numeric regression. Chưa hỗ trợ categorical encoding, classification, time-series ordering, multiple targets, units tự động, differential equations, hay symbolic-regression search. User data chưa được cung cấp trong lần build này, vì vậy acceptance dùng fixture tuyến tính, bậc hai, đa biến và stress data.
