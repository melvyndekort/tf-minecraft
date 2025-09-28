import os
import time
import boto3
from datetime import datetime
import requests
from mcrcon import MCRcon

# ==== Tracking last player ====
last_seen_players = datetime.utcnow()

def send_discord_message(message: str):
    webhook = os.getenv("DISCORD_WEBHOOK")
    if not webhook:
        return
    try:
        requests.post(webhook, json={"content": message})
    except Exception as e:
        print(f"Failed to send Discord message: {e}")

def get_player_count():
    try:
        host = os.getenv("RCON_HOST")
        port = int(os.getenv("RCON_PORT", "25575"))
        password = os.getenv("RCON_PASSWORD")
        
        with MCRcon(host, password, port=port) as mcr:
            resp = mcr.command("list")
            # Example response: "There are 1 of a max of 20 players online: Player1"
            parts = resp.split(":")
            if len(parts) >= 2:
                players = parts[1].strip()
                return len(players.split(", ")) if players else 0
            return 0
    except Exception as e:
        print(f"Failed to get player count: {e}")
        return 0

def shutdown_ecs_service():
    print("Shutting down ECS service...")
    try:
        cluster = os.getenv("ECS_CLUSTER")
        service = os.getenv("ECS_SERVICE")
        region = os.getenv("AWS_REGION", "us-east-1")
        
        client = boto3.client("ecs", region_name=region)
        client.update_service(
            cluster=cluster,
            service=service,
            desiredCount=0
        )
        send_discord_message("Minecraft server is shutting down due to inactivity. 💤")
    except Exception as e:
        print(f"Failed to scale ECS service down: {e}")

def main():
    print("Minecraft idle watcher started.")
    global last_seen_players
    
    idle_minutes = int(os.getenv("IDLE_MINUTES", "15"))
    check_interval = int(os.getenv("CHECK_INTERVAL", "60"))
    
    while True:
        player_count = get_player_count()
        now = datetime.utcnow()

        if player_count > 0:
            last_seen_players = now
            print(f"{now} - Players online: {player_count}")
        else:
            idle_time = now - last_seen_players
            minutes_idle = idle_time.total_seconds() / 60
            print(f"{now} - No players online for {minutes_idle:.1f} minutes")

            if minutes_idle >= idle_minutes:
                shutdown_ecs_service()
                break

        time.sleep(check_interval)

if __name__ == "__main__":
    main()
