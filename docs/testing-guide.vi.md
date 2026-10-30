# Hướng dẫn chạy, test và giải thích dự án

## 1. Dự án hiện làm gì?

Đây là bộ công cụ phát triển module học STEM bằng agents, skills và các module mẫu. Codex điều phối Planner → Architect → Builder → QA. Agents đọc source/case study SINDy để học cách tổ chức input, xử lý dữ liệu, state, UI và kết quả; sau đó điều chỉnh theo brief mới. Việc này cung cấp ví dụ trong context, chưa huấn luyện lại trọng số model.

Có hai sản phẩm demo chạy được: projectile motion và linear regression. Cả hai dùng cùng Flask/HTML shell và Bokeh host. Giao diện demo là sản phẩm học tập; điều phối agents diễn ra trong Codex, chưa có dashboard quản lý agents riêng.

## 2. Chạy demo

Mở Terminal:

```bash
cd /Users/ngoleminh/Documents/multi-agent-platform
./run.sh
```

Mở [http://127.0.0.1:8080](http://127.0.0.1:8080). Chọn một module từ trang chủ. Giữ Terminal mở; Ctrl+C dừng cả Flask và Bokeh. Nếu port đang được dùng:

```bash
./run.sh --port 8088 --bokeh-port 5018
```

Khi chuyển sang máy khác hoặc chưa có `.venv`:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
./run.sh
```

Môi trường đã kiểm chứng là CPython 3.14.0, macOS arm64; file lock ghi chính xác phiên bản. Chưa xác nhận mọi OS/Python khác. Đây là local development host, chưa triển khai public.

## 3. Test thủ công trong khoảng 10 phút

### Projectile motion

1. Chọn speed=20 m/s, angle=30°. Kết quả xấp xỉ time=2.039 s, range=35.312 m, height=5.097 m. Đường bay bắt đầu/kết thúc ở mặt đất.
2. Giữ speed=20, đổi angle=60°. Range gần như giữ nguyên; time và height lớn hơn.
3. Đổi speed=40 ở angle=30°. Time gấp đôi; range và height gấp bốn.
4. Speed=0 hoặc angle=0: kết quả bằng 0, không crash. Angle=90°: bay thẳng đứng, range=0.
5. Đọc ba câu hỏi rồi mở feedback, so sánh với điều vừa quan sát.

### Linear regression

1. Chú ý phương trình thật `y=2x+1` và phương trình fit là hai khái niệm khác nhau. Train dùng hình tròn, test dùng tam giác; đồ thị dưới là residual `y−ŷ`.
2. Đặt noise=0 và bấm **Generate and fit**. Slope gần 2, intercept gần 1, train/test MSE gần 0.
3. Đặt noise=1, n=100, seed=42 và Generate; ghi lại kết quả. Bấm lại cùng cấu hình: kết quả phải giống.
4. Giữ seed/n, tăng noise từ 1 lên 2: residual tăng gấp đôi, MSE xấp xỉ gấp bốn trong mô hình kiểm soát này. Nếu đổi seed/n thì realization/split thay đổi, không so sánh theo quy tắc đó một cách máy móc.
5. Chỉ sửa controls: status phải báo pending, kết quả cũ vẫn ghi đúng cấu hình đã commit. Bấm Generate mới thay đổi kết quả.
6. Thử n=20 và n=300, noise=0 và 5. Không được lỗi hoặc hiển thị kết quả không rõ thuộc cấu hình nào.

### Isolation và layout

Mở cùng module trong hai cửa sổ hoặc một cửa sổ thường và một cửa sổ private. Sửa controls ở một bên; bên kia phải giữ nguyên. Thu hẹp cửa sổ xuống khoảng 390px: đọc được nội dung, thao tác controls và nhìn được plot, không cần cuộn ngang cả trang. Dùng Tab/phím mũi tên để thử controls và mở feedback bằng bàn phím.

## 4. Chạy automated tests

```bash
.venv/bin/python scripts/check_setup.py --runtime codex
.venv/bin/python scripts/sync_runtime.py --check
.venv/bin/python scripts/test_all.py
```

`test_all.py` chạy 32 test methods cho setup, scaffold/Flask/lifecycle, productivity evaluator và hai pilots. Một số test mở port local; môi trường sandbox chặn socket sẽ cần quyền chạy localhost, không được coi đó là lỗi công thức.

Tests bổ sung độc lập và CSV adaptation:

```bash
.venv/bin/python runs/mvp-completion-20261030/independent-science-tests.py
.venv/bin/python -m unittest discover -s evaluations/artifacts/csv-adaptation/tests -v
```

Browser tests (server cần đang chạy ở terminal khác):

```bash
.venv/bin/python -m pip install -r requirements-browser.lock.txt
.venv/bin/python scripts/test_browser.py --base-url http://127.0.0.1:8080 --browser-executable "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
```

Nếu không có Chrome ở đường dẫn trên, bỏ `--browser-executable` và cài Chromium cho Playwright bằng `.venv/bin/python -m playwright install chromium`. Browser tests dùng cửa sổ headless riêng; output mặc định là `output/browser/` với JSON và screenshots. Không phải test mô phỏng DOM: controls thật cập nhật qua kết nối Bokeh server.

## 5. Test chính workflow agents

Mở thư mục dự án này làm working directory trong Codex. Đọc `AGENTS.md`; chọn `$stem-build-module` nếu skill hiện trong selector. Nếu phiên hiện tại chưa tự nạp file mới, yêu cầu đọc trực tiếp `.agents/skills/stem-build-module/SKILL.md` và các role files.

Ví dụ yêu cầu nhỏ:

> Dùng workflow stem-build-module và các subagents để tạo module mới về y=a*x+b cho sinh viên năm nhất. Cho đổi a,b; có đồ thị, ba câu hỏi kèm feedback và tests. Dùng các module trong corpus làm mẫu; ghi source nào đã tham khảo và adaptation. Lưu vào modules/line-explorer, không sửa hai pilot hiện có. Giới hạn hai vòng sửa lỗi; tạo run record và QA evidence.

Quan sát có subagents thực sự, có spec → plan → code → QA và artifacts tương ứng trong `runs/`. Kiểm tra các model/skills agent thực sự dùng; không chỉ nhìn vào việc có các file tên Planner/QA. Phiên đã kiểm chứng dùng truyền role/skill files rõ ràng. Tự nạp custom roles TOML ở phiên mới vẫn cần tự kiểm tra; thiếu Claude không chặn Codex.

Tạo starter thủ công để kiểm tra scaffold (chưa phải agent run):

```bash
.venv/bin/python scripts/create_module.py line-explorer --title "Explore a linear relationship"
./run.sh --module line-explorer
```

Starter chạy được với `y=a*x`; agent có thể mở rộng theo brief. Lệnh từ chối ghi đè module đã tồn tại. Scaffold generation và agent reasoning là hai bước khác nhau; đừng report starter script là tự động tạo mọi loại module khoa học.

## 6. Đọc evidence và gửi feedback

`runs/mvp-completion-20261030/` chứa learning spec, technical plan, Builder reports, QA report, logs và screenshots. `docs/advisor-report.md` là báo cáo tiếng Anh cho thầy/Raghu. `evaluations/report.md` tách kết quả chức năng khỏi giả thuyết tăng năng suất.

Ghi feedback gồm module, controls/data đang dùng, bước tái hiện, điều mong đợi, kết quả thực tế và ảnh nếu cần. Agents đề xuất cập nhật skill/case study dựa trên feedback; module mới chỉ trở thành mẫu đã được duyệt sau review của con người.

Nếu chuyển source SINDy lần nữa:

```bash
.venv/bin/python scripts/configure_source.py sindy "/đường/dẫn/mới/tới/SINDy"
```

Lệnh chỉ đổi vị trí khi mọi hash source đã review vẫn khớp; nếu source thay đổi, cần đọc diff/review rồi mới cập nhật snapshot.

## 7. Nên report điều gì?

Có thể nói đã có workflow chạy bằng Codex subagents thật, shared skills/corpus, scaffold tái sử dụng, hai pilots, độc lập QA và browser verification. Có một lỗi giải thích khoa học đã được QA tìm và Builder sửa; đây là ví dụ cụ thể về giá trị của việc review độc lập.

Chưa có dữ liệu để nói tiết kiệm 30%, cải thiện kết quả học tập hoặc tạo mọi module đúng ngay. Chưa chạy Claude thực tế, chưa làm module neural equation discovery, chưa deploy public. CSV extension là fixture kiểm chứng ingestion ở engine, chưa có UI upload CSV. Những điều này được ghi rõ để tránh trình bày vượt quá evidence.
