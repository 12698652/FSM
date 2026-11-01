# -*- coding: utf-8 -*-
"""一键重新训练与导出：preprocess → (RF基线) → LSTM → export_onnx

为什么需要它
----
真实标签补进 data/labels.csv 后，重训要按顺序跑好几个脚本，顺序错了或
中途失败很难察觉。本脚本把整条链路串起来，并在结尾汇总指标、识别伪标签。

用法（在项目根目录 soft/ 下执行）
----
  python server/retrain.py                  # 真实数据 + LSTM + 导出 ONNX
  python server/retrain.py --source demo    # 用模拟数据跑通管线（验证用）
  python server/retrain.py --with-rf        # 额外训练 RF/GBDT 基线做对比
  python server/retrain.py --deploy         # 训练完成后自动上传模型并重启云端服务

产物
----
  model.pth / metrics.json / data/model.onnx / data/model_meta.json
"""
import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_DIR = os.path.join(ROOT, "server")
PY = sys.executable
SERVER_HOST = "ubuntu@124.221.252.54"
DEPLOY_DIR = "/home/ubuntu/gjn/data"
SERVICE = "gjn-web.service"


def run(title, script, extra=None):
    cmd = [PY, os.path.join(SERVER_DIR, script)] + (extra or [])
    print(f"\n{'=' * 64}\n[步骤] {title}\n$ {' '.join(cmd)}\n{'=' * 64}")
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        print(f"\n[中止] {script} 返回码 {r.returncode}")
        sys.exit(r.returncode)


def summary():
    mp = os.path.join(ROOT, "metrics.json")
    meta = os.path.join(ROOT, "data", "model_meta.json")
    if os.path.exists(mp):
        m = json.load(open(mp, encoding="utf-8"))
        print(f"LSTM 测试准确率 {m.get('accuracy')} | macro-F1 {m.get('macro_f1')} | "
              f"标签来源 {m.get('label_source')}")
    if os.path.exists(meta):
        d = json.load(open(meta, encoding="utf-8"))
        print(f"ONNX 元信息: 窗口 {d.get('window')} | 特征 {len(d.get('feature_names', []))} 维 | "
              f"标签来源 {d.get('label_source')}")
        if str(d.get("label_source", "")).startswith("pseudo"):
            print("⚠ 当前仍是伪标签模型（循环论证），仅供管线/界面演示，不可作为科学结论。")


def deploy():
    for name in ("model.onnx", "model_meta.json"):
        f = os.path.join(ROOT, "data", name)
        if not os.path.exists(f):
            print(f"[中止] 缺少 {f}")
            sys.exit(1)
        print(f"上传 {name} → {SERVER_HOST}:{DEPLOY_DIR}/")
        r = subprocess.run(["scp", f, f"{SERVER_HOST}:{DEPLOY_DIR}/"])
        if r.returncode != 0:
            print("[中止] 上传失败，请检查 SSH 连通与密钥")
            sys.exit(r.returncode)
    print(f"重启云端服务 {SERVICE} ...")
    subprocess.run(["ssh", SERVER_HOST, f"sudo systemctl restart {SERVICE} && systemctl is-active {SERVICE}"])


def main():
    ap = argparse.ArgumentParser(description="一键重新训练与导出")
    ap.add_argument("--source", choices=["real", "demo", "auto"], default="real",
                    help="训练数据来源（默认 real 只用实测数据）")
    ap.add_argument("--split", choices=["session", "stratified", "chrono"], default="session",
                    help="训练/测试切分方式（透传 preprocess.py；stratified/chrono 可把最后场次纳入训练）")
    ap.add_argument("--with-rf", action="store_true", help="额外训练 RF/GBDT 基线做对比")
    ap.add_argument("--deploy", action="store_true", help="训练后自动上传模型并重启云端服务")
    args = ap.parse_args()

    run("数据预处理", "preprocess.py", ["--source", args.source, "--split", args.split])
    if args.with_rf:
        run("RF/GBDT 基线", "train_rf.py")
    run("LSTM+Attention 训练", "train_lstm.py")
    run("导出 ONNX", "export_onnx.py")

    print(f"\n{'=' * 64}\n[汇总]\n{'=' * 64}")
    summary()
    if args.deploy:
        deploy()
        print("\n部署完成。")
    print("\n完成。重训产物已就绪。")


if __name__ == "__main__":
    main()
