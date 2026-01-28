from flask import Flask, request, render_template, jsonify
from datetime import datetime

app = Flask(__name__)

# In-memory store
events = []

def parse_time(time_str):
    """Parse time string to datetime object for sorting"""
    if not time_str:
        return datetime.min
    try:
        # Try parsing ISO format
        return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
    except:
        try:
            # Try parsing with timezone
            return datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%SZ')
        except:
            try:
                # Try parsing without timezone
                return datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            except:
                return datetime.min

def save_event(event):
    # Check for duplicate events
    event_id = f"{event.get('type')}-{event.get('sha', '')}-{event.get('pr_number', '')}-{event.get('time', '')}"
    
    # Use global events list
    global events
    
    for existing in events:
        existing_id = f"{existing.get('type')}-{existing.get('sha', '')}-{existing.get('pr_number', '')}-{existing.get('time', '')}"
        if existing_id == event_id:
            return  # Skip duplicate
    
    events.append(event)
    # Sort events by time (newest first) every time we add a new event
    events = sorted(events, key=lambda x: parse_time(x.get('time', '')), reverse=True)
    if len(events) > 50:
        events = events[:50]

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    github_event = request.headers.get("X-GitHub-Event")
    
    print(f"📢 Received event: {github_event}")
    if data.get('action'):
        print(f"Action: {data.get('action')}")
    
    # ---------------- PUSH EVENT ----------------
    if github_event == "push":
        if data.get("deleted") or data.get("forced"):
            return jsonify({"status": "ignored"}), 200
            
        commits = data.get("commits", [])
        if not commits:
            return jsonify({"status": "no commits"}), 200
            
        for commit in commits:
            commit_msg = commit.get("message", "").lower()
            # Skip merge commits
            if "merge" in commit_msg and ("pull request" in commit_msg or "pr" in commit_msg):
                continue
                
            save_event({
                "type": "PUSH",
                "repo": data["repository"]["full_name"],
                "author": commit["author"]["name"],
                "message": commit["message"][:100],
                "time": commit["timestamp"],
                "sha": commit["id"][:7]
            })

    # ---------------- PULL REQUEST EVENTS ----------------
    elif github_event == "pull_request":
        action = data.get("action")
        pr = data.get("pull_request")
        
        print(f"📋 PR #{pr.get('number') if pr else 'N/A'} - Action: {action}")
        
        # PR CREATED
        if action == "opened":
            save_event({
                "type": "PR_CREATED",
                "repo": pr["base"]["repo"]["full_name"],
                "author": pr["user"]["login"],
                "message": f"PR opened: {pr['title']}",
                "time": pr["created_at"],
                "pr_number": pr["number"],
                "pr_state": pr["state"]
            })
        
        # PR MERGED
        elif action == "closed" and pr and pr.get("merged") == True:
            save_event({
                "type": "PR_MERGED",
                "repo": pr["base"]["repo"]["full_name"],
                "author": pr["merged_by"]["login"] if pr.get("merged_by") else pr["user"]["login"],
                "message": f"PR merged: {pr['title']}",
                "time": pr["merged_at"],
                "pr_number": pr["number"]
            })
            
            # Also save the merge commit
            if pr.get("merge_commit_sha"):
                save_event({
                    "type": "MERGE_COMMIT",
                    "repo": pr["base"]["repo"]["full_name"],
                    "author": pr["merged_by"]["login"] if pr.get("merged_by") else pr["user"]["login"],
                    "message": f"Merge commit for PR #{pr['number']}: {pr['title']}",
                    "time": pr["merged_at"],
                    "sha": pr.get("merge_commit_sha", "")[:7],
                    "pr_number": pr["number"]
                })
        
        # PR CLOSED (not merged)
        elif action == "closed" and pr and not pr.get("merged"):
            save_event({
                "type": "PR_CLOSED",
                "repo": pr["base"]["repo"]["full_name"],
                "author": pr["user"]["login"],
                "message": f"PR closed without merge: {pr['title']}",
                "time": pr["closed_at"],
                "pr_number": pr["number"]
            })
        
        # PR UPDATED (new commits added)
        elif action == "synchronize":
            save_event({
                "type": "PR_UPDATED",
                "repo": pr["base"]["repo"]["full_name"],
                "author": pr["user"]["login"],
                "message": f"New commits added to PR #{pr['number']}: {pr['title']}",
                "time": datetime.utcnow().isoformat() + "Z",
                "pr_number": pr["number"]
            })

    return jsonify({"status": "ok"}), 200

@app.route("/events", methods=["GET"])
def get_events():
    # Events are already sorted by time (newest first)
    return jsonify(events)

@app.route("/debug", methods=["GET"])
def debug():
    """Debug endpoint to see recent events with details"""
    # Show timestamps for debugging
    event_details = []
    for e in events[-10:]:
        event_details.append({
            "type": e.get("type"),
            "time": e.get("time"),
            "parsed_time": str(parse_time(e.get("time"))),
            "message": e.get("message")[:50] if e.get("message") else ""
        })
    
    return jsonify({
        "total_events": len(events),
        "events": events[-10:],
        "event_types": list(set(e["type"] for e in events)),
        "time_debug": event_details
    })

@app.route("/resort", methods=["POST"])
def resort_events():
    """Manually resort events (for debugging)"""
    global events
    events = sorted(events, key=lambda x: parse_time(x.get('time', '')), reverse=True)
    return jsonify({
        "status": "resorted",
        "count": len(events),
        "latest_time": events[0].get("time") if events else None
    })

@app.route("/clear", methods=["POST"])
def clear_events():
    global events
    events = []
    return jsonify({"status": "cleared", "count": 0})

@app.route("/")
def home():
    # Events are already sorted
    return render_template("index.html", events=events)

if __name__ == "__main__":
    app.run(debug=True, port=5000)