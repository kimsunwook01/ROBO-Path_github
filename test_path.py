import logging
from src.infrastructure.database.client import get_supabase_admin_client
from src.infrastructure.database.supabase_edge_repo import SupabaseEdgeRepository
from src.infrastructure.database.supabase_robot_repo import SupabaseRobotRepository
from src.infrastructure.database.supabase_node_repo import SupabaseNodeRepository
from src.application.services.path_planning_service import PathPlanningService
from src.domain.algorithms.a_star import build_graph
import itertools

logging.basicConfig(level=logging.INFO)

db_client = get_supabase_admin_client()
edge_repo = SupabaseEdgeRepository(db_client)
robot_repo = SupabaseRobotRepository(db_client)
node_repo = SupabaseNodeRepository(db_client)
path_service = PathPlanningService(node_repo, edge_repo)

robot = robot_repo.get_robot_by_name("Wheeled-01")
nodes = node_repo.get_all_nodes()
edges = edge_repo.get_all_edges()

print("Robot:", robot.name)
print("Weight Profile:", robot.weight_profile)
print("Nodes:", len(nodes))
print("Edges:", len(edges))

pickups = [n for n in nodes if getattr(n, "terrain_tag", "") == "Node_Pickup"]
destinations = [n for n in nodes if getattr(n, "terrain_tag", "") == "Node_Destination"]

print("Pickups:", len(pickups))
print("Destinations:", len(destinations))

graph = build_graph(nodes, edges, robot)
edges_in_graph = sum(len(adj) for adj in graph.values())
print("Edges in Graph:", edges_in_graph)

import random
for dest in random.sample(destinations, min(5, len(destinations))):
    path = path_service.find_path(pickups[0].id, dest.id, robot)
    print(f"Path from {pickups[0].name} to {dest.name}: len={len(path)}")

