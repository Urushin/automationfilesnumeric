import json

transcript_path = "/Users/issam/.gemini/antigravity-ide/brain/1a560cd2-9a41-4bb1-a0fc-06e5a057a0a6/.system_generated/logs/transcript.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        try:
            data = json.loads(line)
            step_idx = data.get("step_index")
            if 1 <= step_idx <= 40:
                print(f"Step {step_idx}: type={data.get('type')}, status={data.get('status')}")
                content = data.get("content", "")
                tool_calls = data.get("tool_calls", [])
                if content:
                    print(f"  Content length: {len(content)}")
                    print(f"  Content: {content[:300]!r}")
                if tool_calls:
                    print(f"  Tool calls: {[tc.get('name') for tc in tool_calls]}")
                    for tc in tool_calls:
                        args = tc.get("args", {})
                        if args.get("TargetFile"):
                            print(f"    TargetFile: {args.get('TargetFile')}")
                        if args.get("TargetContent"):
                            print(f"    TargetContent: {args.get('TargetContent')[:100]!r}")
                        if args.get("ReplacementContent"):
                            print(f"    ReplacementContent: {args.get('ReplacementContent')[:100]!r}")
        except Exception as e:
            pass

        
print("Done.")
