import os
from typing import List
from uuid import UUID

from src.domain.models import Edge, Node, Robot, MissionLog
from src.domain.algorithms.a_star import a_star_search
from src.application.interfaces.node_repository import NodeRepository
from src.application.interfaces.edge_repository import EdgeRepository

class PathPlanningService:
    """
    A* 알고리즘과 DB 인프라(Repository)를 연결하여 플랫폼 맞춤형 최적 경로를 탐색하는 서비스입니다.
    """
    def __init__(self, node_repo: NodeRepository, edge_repo: EdgeRepository):
        self.node_repo = node_repo
        self.edge_repo = edge_repo

    def find_path(self, start_node_id: UUID, goal_node_id: UUID, robot: Robot) -> List[UUID]:
        """
        출발지와 도착지 노드 ID, 로봇 정보를 받아 최적 경로의 노드 ID 리스트를 반환합니다.
        
        Args:
            start_node_id: 출발지 노드 UUID
            goal_node_id: 도착지 노드 UUID
            robot: 경로 주행을 수행할 로봇 객체 (플랫폼, 가중치 프로필 정보 포함)
            
        Returns:
            List[UUID]: 최적 경로를 구성하는 노드 ID의 순차적 리스트. 경로를 찾지 못하면 빈 리스트 반환.
        """
        # 1. 출발지 및 도착지 노드 검증
        start_node = self.node_repo.get_node_by_id(start_node_id)
        if not start_node:
            raise ValueError(f"Start node not found: {start_node_id}")
            
        goal_node = self.node_repo.get_node_by_id(goal_node_id)
        if not goal_node:
            raise ValueError(f"Goal node not found: {goal_node_id}")

        # 2. 전체 탐색 공간(노드, 엣지) 로드
        # 주의: 맵의 크기가 매우 클 경우 성능 최적화를 위해 동적 로딩이 필요할 수 있습니다.
        nodes = self.node_repo.get_all_nodes()
        edges = self.edge_repo.get_all_edges()

        # 3. A* 알고리즘 호출
        path = a_star_search(
            start_node=start_node,
            goal_node=goal_node,
            nodes=nodes,
            edges=edges,
            robot=robot
        )

        return path
