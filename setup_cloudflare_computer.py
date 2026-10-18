import os
import sys
import shutil
import subprocess
from pathlib import Path

# Configuration
PROJECT_DIR_NAME = "cloudflare-computer-demo"

PACKAGE_JSON = """{
  "name": "cloudflare-computer-demo",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "wrangler dev",
    "deploy": "wrangler deploy",
    "types": "wrangler types"
  },
  "dependencies": {
    "@cloudflare/computer": "^0.5.0"
  },
  "devDependencies": {
    "@types/node": "^22.0.0",
    "typescript": "^5.7.0",
    "wrangler": "^4.149.0"
  }
}
"""

TSCONFIG_JSON = """{
  "compilerOptions": {
    "target": "ESNext",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "types": [
      "./worker-configuration.d.ts"
    ],
    "strict": true,
    "skipLibCheck": true,
    "isolatedModules": true,
    "noEmit": true
  },
  "include": [
    "src/**/*.ts",
    "worker-configuration.d.ts"
  ]
}
"""

WRANGLER_JSONC = """{
  "$schema": "node_modules/wrangler/config-schema.json",
  "name": "my-agent-computer",
  "main": "src/index.ts",
  "compatibility_date": "2024-10-01",
  "compatibility_flags": [
    "nodejs_compat",
    "experimental"
  ],
  "durable_objects": {
    "bindings": [
      {
        "name": "Agent",
        "class_name": "Agent"
      }
    ]
  },
  "migrations": [
    {
      "tag": "v1",
      "new_sqlite_classes": [
        "Agent"
      ]
    }
  ],
  "worker_loaders": [
    {
      "binding": "LOADER"
    }
  ]
}
"""

INDEX_TS = """import { DurableObject } from "cloudflare:workers";
import { getWorkspace, WorkspaceServiceProxy, withWorkspace } from "@cloudflare/computer";
import { WorkerShellBackend } from "@cloudflare/computer/backends/worker-shell";
import curl from "@cloudflare/computer/shell/curl";

// Re-export so the runtime can wrap WorkspaceServiceProxy into a loopback Fetcher binding.
export { WorkspaceServiceProxy };

// 1. Durable Object with SQLite-backed virtual computer workspace
export class Agent extends withWorkspace(
  class extends DurableObject {},
  (self) => {
    const { ctx, env } = self as unknown as { ctx: DurableObjectState; env: Env };
    return {
      storage: ctx.storage,
      backends: [
        new WorkerShellBackend({
          loader: env.LOADER,
          workspace: { binding: "Agent", id: ctx.id.toString() },
          ctx,
          commands: [curl],
        }),
      ],
    };
  },
) {}

// 2. HTTP Server to interact with the computer
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // Support multiple agent sessions via ?workspace=
    const workspaceId = url.searchParams.get("workspace") || "default-agent";
    const doId = env.Agent.idFromName(workspaceId);
    const stub = env.Agent.get(doId);

    // Connect to the workspace
    const ws = await getWorkspace(stub as unknown as Parameters<typeof getWorkspace>[0]);

    // POST /exec - Execute a shell command
    if (url.pathname === "/exec" && request.method === "POST") {
      try {
        const body = (await request.json()) as { cmd?: string };
        if (!body.cmd) {
          return Response.json({ error: "Missing 'cmd' in JSON body" }, { status: 400 });
        }

        using run = await ws.runtime.exec(body.cmd);
        const { stdout, stderr, exitCode } = await run.result();

        return Response.json({ exitCode, stdout, stderr });
      } catch (err: any) {
        return Response.json({ error: err.message }, { status: 500 });
      }
    }

    // POST /file?path=... - Write a file
    if (url.pathname === "/file" && request.method === "POST") {
      const filePath = url.searchParams.get("path") || "/workspace/notes.txt";
      const content = await request.text();

      await ws.fs.writeFile(filePath, content);
      return Response.json({ success: true, path: filePath });
    }

    // GET /file?path=... - Read a file
    if (url.pathname === "/file" && request.method === "GET") {
      const filePath = url.searchParams.get("path") || "/workspace/notes.txt";
      try {
        const content = await ws.fs.readFile(filePath, "utf8");
        return new Response(content, {
          headers: { "Content-Type": "text/plain; charset=utf-8" },
        });
      } catch (err: any) {
        return Response.json({ error: `File not found: ${err.message}` }, { status: 404 });
      }
    }

    return new Response(
      [
        "🚀 Cloudflare Computer is running!",
        "",
        "Available Endpoints:",
        "  POST /exec        -> Run bash command { 'cmd': 'ls -la /workspace' }",
        "  POST /file?path=  -> Write file with request body",
        "  GET  /file?path=  -> Read file contents",
      ].join("\\n"),
      { status: 200 }
    );
  },
} satisfies ExportedHandler<Env>;
"""

GITIGNORE = """node_modules/
.wrangler/
dist/
worker-configuration.d.ts
"""

TEST_CLIENT_PY = """import json
import urllib.request
import urllib.parse

BASE_URL = "http://localhost:8787"

def write_file(path: str, content: str):
    url = f"{BASE_URL}/file?path={urllib.parse.quote(path)}"
    req = urllib.request.Request(url, data=content.encode("utf-8"), method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def read_file(path: str):
    url = f"{BASE_URL}/file?path={urllib.parse.quote(path)}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8")

def exec_cmd(cmd: str):
    url = f"{BASE_URL}/exec"
    payload = json.dumps({"cmd": cmd}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

if __name__ == "__main__":
    print("--- 1. Writing a test script to virtual computer ---")
    write_resp = write_file("/workspace/hello.sh", "#!/bin/bash\\necho 'Hello from inside Cloudflare Computer!'")
    print("Write Response:", write_resp)

    print("\\n--- 2. Reading file back from virtual computer ---")
    content = read_file("/workspace/hello.sh")
    print("File Content:\\n", content)

    print("\\n--- 3. Executing commands in the agent's shell ---")
    exec_resp = exec_cmd("cat /workspace/hello.sh && ls -la /workspace")
    print("Exit Code:", exec_resp.get("exitCode"))
    print("Stdout:\\n" + exec_resp.get("stdout", ""))
"""

def run_cmd(cmd, cwd):
    """Run a shell command on Windows safely."""
    print(f"--> Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    res = subprocess.run(cmd, cwd=cwd, shell=True, check=False)
    if res.returncode != 0:
        print(f"[!] Warning: Command exited with code {res.returncode}")
        return False
    return True

def main():
    print("==================================================")
    print("   Cloudflare Computer Windows Setup Script")
    print("==================================================")

    # 1. Verify Node.js and npm exist
    if not shutil.which("node"):
        print("[X] Error: Node.js is not found in PATH.")
        print("    Install it via winget: winget install OpenJS.NodeJS.LTS")
        sys.exit(1)

    if not shutil.which("npm"):
        print("[X] Error: npm is not found in PATH.")
        sys.exit(1)

    print("[✓] Node.js and npm detected.")

    # 2. Create project directory
    target_dir = Path.cwd() / PROJECT_DIR_NAME
    target_dir.mkdir(parents=True, exist_ok=True)
    src_dir = target_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    print(f"[✓] Created project directory: {target_dir}")

    # 3. Write project files
    files = {
        target_dir / "package.json": PACKAGE_JSON,
        target_dir / "tsconfig.json": TSCONFIG_JSON,
        target_dir / "wrangler.jsonc": WRANGLER_JSONC,
        target_dir / ".gitignore": GITIGNORE,
        src_dir / "index.ts": INDEX_TS,
        target_dir / "test_computer.py": TEST_CLIENT_PY,
    }

    for path, content in files.items():
        path.write_text(content.strip() + "\n", encoding="utf-8")
        print(f"    - Created: {path.name}")

    print("\\n[✓] All configuration and source files created successfully.")

    # 4. Install npm packages
    print("\\n--> Installing npm packages (this may take a minute)...")
    success = run_cmd("npm install", cwd=target_dir)
    if not success:
        print("[!] npm install encountered an issue. You can retry inside the folder manually.")

    # 5. Generate Wrangler types
    print("\\n--> Generating Cloudflare Worker types...")
    run_cmd("npx wrangler types", cwd=target_dir)

    print("\\n==================================================")
    print("🎉 Setup Complete!")
    print("==================================================")
    print(f"\\nTo run and test your Cloudflare Computer:\\n")
    print(f"  1. Navigate to the project directory:")
    print(f"     cd {PROJECT_DIR_NAME}\\n")
    print(f"  2. Start the local development server:")
    print(f"     npm run dev\\n")
    print(f"  3. In a separate terminal, test it with Python:")
    print(f"     python test_computer.py\\n")

if __name__ == "__main__":
    main()
