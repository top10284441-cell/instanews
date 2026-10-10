@echo off
chcp 65001 > nul
cd /d "d:\사용자파일\바탕화면\antigravity\instagrm_Auto"
python run_telegram_pipeline.py >> "d:\사용자파일\바탕화면\antigravity\instagrm_Auto\telegram_schedule.log" 2>&1
