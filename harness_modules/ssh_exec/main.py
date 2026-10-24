import subprocess

NODES = {
    "node-A": ("root@47.96.87.147", None),
    "node-B": ("root@10.0.0.2", "root@47.96.87.147"), 
}

def run(params):
    host = params.get("host", "node-A")
    cmd = params.get("command", "")
    
    if not cmd:
        return {"success": False, "error": "命令不能为空"}
        
    forbidden = ["rm -rf /", "mkfs", "> /dev/sda"]
    for f in forbidden:
        if f in cmd:
            return {"success": False, "error": f"检测到极度危险命令 '{f}'，已强制拦截"}

    target, jump = NODES.get(host, (host, None))
    key_path = "C:/Users/xiaomai/.ssh/id_rsa_sases"
    
    # 强制使用私钥、禁用密码提示、禁用 host 检查
    common_opts = f"-i {key_path} -o StrictHostKeyChecking=no -o BatchMode=yes -o PasswordAuthentication=no -o ConnectTimeout=5"
    
    ssh_cmd = ["ssh"] + common_opts.split()
    
    if jump:
        # 核心修复：在 ProxyCommand 里也必须带上私钥和禁用密码
        proxy_cmd = f"ssh {common_opts} -W %h:%p {jump}"
        ssh_cmd.extend(["-o", f"ProxyCommand={proxy_cmd}"])
        
    ssh_cmd.extend([target, cmd])
        
    try:
        res = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=15, encoding='utf-8', errors='replace')
        return {
            "success": res.returncode == 0,
            "stdout": res.stdout,
            "stderr": res.stderr,
            "returncode": res.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "SSH 执行超时"}
    except Exception as e:
        return {"success": False, "error": str(e)}
