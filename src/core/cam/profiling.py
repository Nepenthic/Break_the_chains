import time
import psutil
import cProfile
import pstats
import io
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
import numpy as np
from .simulation import MaterialSimulator

@dataclass
class PerformanceMetrics:
    """Performance metrics for material simulation."""
    cpu_time: float
    memory_usage: float
    thread_count: int
    voxel_count: int
    refinement_count: int
    coarsening_count: int
    operation_times: Dict[str, float]
    
    def generate_report(self) -> str:
        """
        Generate a human-readable performance report.
        
        Returns:
            String containing formatted performance metrics
        """
        report = []
        report.append("Performance Report")
        report.append("================")
        report.append(f"CPU Time: {self.cpu_time:.2f} seconds")
        report.append(f"Memory Usage: {self.memory_usage:.2f} MB")
        report.append(f"Thread Count: {self.thread_count}")
        report.append(f"Voxel Count: {self.voxel_count}")
        report.append(f"Refinement Count: {self.refinement_count}")
        report.append(f"Coarsening Count: {self.coarsening_count}")
        report.append("\nOperation Times:")
        for op, duration in self.operation_times.items():
            report.append(f"  {op}: {duration:.3f} seconds")
        return "\n".join(report)

class Profiler:
    """Profiler for material simulation."""
    
    def __init__(self):
        """Initialize profiler."""
        self.start_time = None
        self.start_memory = None
        self.operation_times = {}
        self.current_operation = None
        self.operation_start = None
        
    def start(self) -> None:
        """Start profiling session."""
        self.start_time = time.time()
        self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.operation_times = {}
        
    def stop(self) -> PerformanceMetrics:
        """
        Stop profiling session and return metrics.
        
        Returns:
            PerformanceMetrics object containing collected metrics
        """
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        return PerformanceMetrics(
            cpu_time=end_time - self.start_time,
            memory_usage=end_memory - self.start_memory,
            thread_count=psutil.Process().num_threads(),
            voxel_count=0,  # Will be set by simulator
            refinement_count=0,  # Will be set by simulator
            coarsening_count=0,  # Will be set by simulator
            operation_times=self.operation_times
        )
        
    def start_operation(self, name: str) -> None:
        """
        Start timing an operation.
        
        Args:
            name: Name of the operation
        """
        self.current_operation = name
        self.operation_start = time.time()
        
    def stop_operation(self) -> None:
        """Stop timing the current operation."""
        if self.current_operation and self.operation_start:
            duration = time.time() - self.operation_start
            self.operation_times[self.current_operation] = duration
            self.current_operation = None
            self.operation_start = None

def profile_simulation(
    simulator: MaterialSimulator,
    toolpath: List[np.ndarray],
    tool_diameter: float,
    islands: Optional[List[Dict[str, Union[List[np.ndarray], float]]]] = None
) -> PerformanceMetrics:
    """
    Profile a complete material simulation.
    
    Args:
        simulator: MaterialSimulator instance
        toolpath: List of tool positions
        tool_diameter: Diameter of the cutting tool
        islands: Optional list of islands to preserve
        
    Returns:
        PerformanceMetrics object containing simulation metrics
    """
    profiler = Profiler()
    profiler.start()
    
    # Run simulation
    simulator.simulate_toolpath(toolpath, tool_diameter, islands)
    
    # Get metrics from simulator
    metrics = profiler.stop()
    sim_metrics = simulator.get_performance_metrics()
    
    # Update metrics with simulator data
    metrics.voxel_count = sim_metrics['voxel_count']
    metrics.refinement_count = sim_metrics['refinement_count']
    metrics.coarsening_count = sim_metrics['coarsening_count']
    
    return metrics

def profile_function(func):
    """
    Decorator to profile a function using cProfile.
    
    Args:
        func: Function to profile
        
    Returns:
        Decorated function that profiles execution
    """
    def wrapper(*args, **kwargs):
        pr = cProfile.Profile()
        try:
            return pr.runcall(func, *args, **kwargs)
        finally:
            s = io.StringIO()
            ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
            ps.print_stats()
            print(s.getvalue())
    return wrapper

def compare_simulations(
    uniform_sim: MaterialSimulator,
    adaptive_sim: MaterialSimulator,
    toolpath: List[np.ndarray],
    tool_diameter: float,
    islands: Optional[List[Dict[str, Union[List[np.ndarray], float]]]] = None
) -> Dict:
    """
    Compare performance between uniform and adaptive voxel grids.
    
    Args:
        uniform_sim: Simulator with uniform voxel grid
        adaptive_sim: Simulator with adaptive voxel grid
        toolpath: List of tool positions
        tool_diameter: Diameter of the cutting tool
        islands: Optional list of islands to preserve
        
    Returns:
        Dictionary containing comparison results
    """
    # Profile uniform grid simulation
    uniform_metrics = profile_simulation(
        uniform_sim,
        toolpath,
        tool_diameter,
        islands
    )
    
    # Profile adaptive grid simulation
    adaptive_metrics = profile_simulation(
        adaptive_sim,
        toolpath,
        tool_diameter,
        islands
    )
    
    # Calculate improvements
    improvements = {
        'cpu_time': (uniform_metrics.cpu_time - adaptive_metrics.cpu_time) / uniform_metrics.cpu_time * 100,
        'memory_usage': (uniform_metrics.memory_usage - adaptive_metrics.memory_usage) / uniform_metrics.memory_usage * 100,
        'voxel_count': (uniform_metrics.voxel_count - adaptive_metrics.voxel_count) / uniform_metrics.voxel_count * 100
    }
    
    return {
        'uniform_metrics': uniform_metrics,
        'adaptive_metrics': adaptive_metrics,
        'improvements': improvements
    } 