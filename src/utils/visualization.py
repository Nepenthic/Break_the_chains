import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import os

class PerformanceVisualizer:
    """Generates visualizations for performance test results."""
    
    def __init__(self, output_dir='reports'):
        """Initialize visualizer with output directory."""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Set style for better-looking plots
        plt.style.use('seaborn')
    
    def plot_transform_durations(self, shape_counts, durations, test_type='batch'):
        """Generate line plot of transform durations vs shape count."""
        plt.figure(figsize=(10, 6))
        plt.plot(shape_counts, durations, marker='o', linewidth=2, markersize=8)
        
        plt.xlabel('Shape Count', fontsize=12)
        plt.ylabel('Duration (ms)', fontsize=12)
        plt.title(f'{test_type.title()} Transform Duration vs Shape Count', 
                 fontsize=14, pad=20)
        
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        # Add trend line
        z = np.polyfit(shape_counts, durations, 1)
        p = np.poly1d(z)
        plt.plot(shape_counts, p(shape_counts), "r--", alpha=0.8, 
                label=f'Trend (slope: {z[0]:.2f})')
        
        plt.legend()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{self.output_dir}/transform_duration_{test_type}_{timestamp}.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        return filename
    
    def plot_memory_usage(self, shape_counts, memory_usage, test_type='batch'):
        """Generate bar plot of memory usage per test scenario."""
        plt.figure(figsize=(10, 6))
        
        bars = plt.bar(range(len(shape_counts)), memory_usage, 
                      color='skyblue', alpha=0.7)
        
        # Add value labels on top of bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}MB',
                    ha='center', va='bottom')
        
        plt.xticks(range(len(shape_counts)), shape_counts, rotation=0)
        plt.xlabel('Shape Count', fontsize=12)
        plt.ylabel('Memory Usage (MB)', fontsize=12)
        plt.title(f'Memory Usage per {test_type.title()} Test Scenario', 
                 fontsize=14, pad=20)
        
        plt.grid(True, axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{self.output_dir}/memory_usage_{test_type}_{timestamp}.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        return filename
    
    def plot_performance_scatter(self, x_values, y_values, 
                               x_label, y_label, title):
        """Generate scatter plot with trend line."""
        plt.figure(figsize=(10, 6))
        
        plt.scatter(x_values, y_values, alpha=0.6, s=100)
        
        # Add trend line
        z = np.polyfit(x_values, y_values, 1)
        p = np.poly1d(z)
        plt.plot(x_values, p(x_values), "r--", alpha=0.8,
                label=f'Trend (slope: {z[0]:.2f})')
        
        plt.xlabel(x_label, fontsize=12)
        plt.ylabel(y_label, fontsize=12)
        plt.title(title, fontsize=14, pad=20)
        
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        plt.tight_layout()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_title = title.lower().replace(' ', '_')
        filename = f'{self.output_dir}/scatter_{safe_title}_{timestamp}.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        return filename
    
    def generate_html_report(self, report_data, image_files):
        """Generate HTML report with embedded visualizations."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_file = f'{self.output_dir}/performance_report_{timestamp}.html'
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Performance Test Report - {timestamp}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .metrics {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .metric-box {{ 
                    padding: 20px; 
                    background: #f5f5f5; 
                    border-radius: 5px;
                    text-align: center;
                }}
                .visualization {{ margin: 30px 0; }}
                .visualization img {{ max-width: 100%; height: auto; }}
                .recommendations {{ margin: 30px 0; }}
                .recommendation {{ 
                    padding: 10px; 
                    margin: 10px 0; 
                    border-left: 4px solid #ccc; 
                }}
                .high {{ border-left-color: #ff4444; }}
                .medium {{ border-left-color: #ffbb33; }}
                .low {{ border-left-color: #00C851; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Performance Test Report</h1>
                    <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <div class="metrics">
                    <div class="metric-box">
                        <h3>Tests Run</h3>
                        <p>{report_data['test_results']['tests_run']}</p>
                    </div>
                    <div class="metric-box">
                        <h3>Success Rate</h3>
                        <p>{(report_data['test_results']['tests_run'] - 
                           report_data['test_results']['failures']) / 
                           report_data['test_results']['tests_run'] * 100:.1f}%</p>
                    </div>
                </div>
                
                <div class="visualizations">
                    <h2>Performance Visualizations</h2>
                    {self._generate_image_sections(image_files)}
                </div>
                
                <div class="recommendations">
                    <h2>Recommendations</h2>
                    {self._generate_recommendation_sections(report_data['recommendations'])}
                </div>
                
                <div class="system-info">
                    <h2>System Information</h2>
                    {self._generate_system_info_section(report_data['system_info'])}
                </div>
            </div>
        </body>
        </html>
        """
        
        with open(html_file, 'w') as f:
            f.write(html_content)
        
        return html_file
    
    def _generate_image_sections(self, image_files):
        """Generate HTML sections for visualization images."""
        sections = []
        for image_file in image_files:
            filename = os.path.basename(image_file)
            title = filename.split('_')[0].title()
            sections.append(f"""
                <div class="visualization">
                    <h3>{title} Visualization</h3>
                    <img src="{image_file}" alt="{title} visualization">
                </div>
            """)
        return '\n'.join(sections)
    
    def _generate_recommendation_sections(self, recommendations):
        """Generate HTML sections for recommendations."""
        sections = []
        for rec in recommendations:
            sections.append(f"""
                <div class="recommendation {rec['priority']}">
                    <h4>{rec['message']}</h4>
                    <p>{rec['details']}</p>
                </div>
            """)
        return '\n'.join(sections)
    
    def _generate_system_info_section(self, system_info):
        """Generate HTML section for system information."""
        items = []
        for key, value in system_info.items():
            if 'memory' in key.lower():
                value = f"{value / (1024**3):.2f} GB"
            items.append(f"<li><strong>{key.replace('_', ' ').title()}:</strong> {value}</li>")
        return f"<ul>{''.join(items)}</ul>" 