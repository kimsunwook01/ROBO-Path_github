# 가상환경 활성화
    # conda activate robopath

# 가상환경 비활성화
    # conda deactivate

# conda 라이브러리 목록 관리 파일 생성 및 갱신 명령어
    # conda env export --from-history > environment.yml
    # 해당 명령어는 conda install로 설치한 기록만 확인하고 갱신한다.

# pip 라이브러리 목록 관리 파일 생성 및 갱신 명령어
    # pip freeze > requirements.txt
    # 해당 명령어는 pip install로 설치한 기록만 확인하고 갱신한다.

# 맥미니 원격 접속을 위한 아이디 ip

    # cd ~/ROBO-Path_project
    # conda activate robopath

    # 맥미니 서버의 모든 로봇 상태를 Idle로 변경(안전모드)
    # python -c "from src.infrastructure.database.client import get_supabase_admin_client as g; c=g(); print(c.table('robots').update({'status':'Idle'}).neq('name','').execute().data)"

# 미션 시작
    # python src/presentation/ros2_bridge/start_mission.py Wheeled-01
    # python src/presentation/ros2_bridge/start_mission.py Wheeled-02
    # python src/presentation/ros2_bridge/start_mission.py Wheeled-03
    # python src/presentation/ros2_bridge/start_mission.py Wheeled-04
    # python src/presentation/ros2_bridge/start_mission.py Wheeled-05
    # python src/presentation/ros2_bridge/start_mission.py Legged-01
    # python src/presentation/ros2_bridge/start_mission.py Legged-02
    # python src/presentation/ros2_bridge/start_mission.py Legged-03
    # python src/presentation/ros2_bridge/start_mission.py Legged-04

https://robo-pathapp-2kotzoqnynm4cejzz6rd4w.streamlit.app/