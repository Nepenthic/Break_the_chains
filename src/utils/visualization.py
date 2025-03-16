import plotly.graph_objs as go
import plotly.io as pio
import numpy as np
from datetime import datetime
import os

class PerformanceVisualizer:
    """Generates interactive visualizations for performance test results."""
    
    def __init__(self, output_dir='reports'):
        """Initialize visualizer with output directory."""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Set default Plotly template
        pio.templates.default = "plotly_white"
    
    def plot_transform_durations(self, shape_counts, durations, test_type='batch'):
        """Generate interactive line plot of transform durations vs shape count."""
        fig = go.Figure()
        
        # Add duration scatter plot
        fig.add_trace(go.Scatter(
            x=shape_counts,
            y=durations,
            mode='lines+markers',
            name='Duration (ms)',
            line=dict(width=2, color='#1f77b4'),
            marker=dict(size=10),
            hovertemplate='Shape Count: %{x}<br>Duration: %{y:.2f} ms<extra></extra>'
        ))
        
        # Add trend line
        z = np.polyfit(shape_counts, durations, 1)
        p = np.poly1d(z)
        trend_x = np.array(shape_counts)
        trend_y = p(trend_x)
        fig.add_trace(go.Scatter(
            x=trend_x,
            y=trend_y,
            mode='lines',
            name=f'Trend (slope: {z[0]:.2f})',
            line=dict(dash='dash', color='#ff7f0e'),
            hovertemplate='Shape Count: %{x}<br>Predicted: %{y:.2f} ms<extra></extra>'
        ))
        
        fig.update_layout(
            title=dict(
                text=f'{test_type.title()} Transform Duration vs Shape Count',
                x=0.5,
                font=dict(size=20)
            ),
            xaxis_title=dict(text='Shape Count', font=dict(size=14)),
            yaxis_title=dict(text='Duration (ms)', font=dict(size=14)),
            hovermode='closest',
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="right",
                x=0.99
            ),
            margin=dict(t=100, l=80, r=80, b=80)
        )
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{self.output_dir}/transform_duration_{test_type}_{timestamp}.html'
        fig.write_html(
            filename,
            include_plotlyjs='cdn',
            full_html=True,
            config={'displayModeBar': True, 'responsive': True}
        )
        
        return filename
    
    def plot_memory_usage(self, shape_counts, memory_usage, test_type='batch'):
        """Generate interactive bar plot of memory usage per test scenario."""
        fig = go.Figure()
        
        # Add memory usage bars
        fig.add_trace(go.Bar(
            x=shape_counts,
            y=memory_usage,
            name='Memory Usage',
            marker_color='#2ecc71',
            opacity=0.7,
            hovertemplate='Shape Count: %{x}<br>Memory: %{y:.1f} MB<extra></extra>'
        ))
        
        # Add value labels on top of bars
        for i, value in enumerate(memory_usage):
            fig.add_annotation(
                x=shape_counts[i],
                y=value,
                text=f'{value:.1f} MB',
                showarrow=False,
                yshift=10,
                font=dict(size=12)
            )
        
        fig.update_layout(
            title=dict(
                text=f'Memory Usage per {test_type.title()} Test Scenario',
                x=0.5,
                font=dict(size=20)
            ),
            xaxis_title=dict(text='Shape Count', font=dict(size=14)),
            yaxis_title=dict(text='Memory Usage (MB)', font=dict(size=14)),
            hovermode='closest',
            showlegend=False,
            margin=dict(t=100, l=80, r=80, b=80)
        )
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{self.output_dir}/memory_usage_{test_type}_{timestamp}.html'
        fig.write_html(
            filename,
            include_plotlyjs='cdn',
            full_html=True,
            config={'displayModeBar': True, 'responsive': True}
        )
        
        return filename
    
    def plot_performance_scatter(self, x_values, y_values, x_label, y_label, title):
        """Generate interactive scatter plot with trend line."""
        fig = go.Figure()
        
        # Add scatter plot
        fig.add_trace(go.Scatter(
            x=x_values,
            y=y_values,
            mode='markers',
            name='Data Points',
            marker=dict(
                size=12,
                color='#3498db',
                opacity=0.6,
                line=dict(width=1, color='#2980b9')
            ),
            hovertemplate=f'{x_label}: %{{x}}<br>{y_label}: %{{y:.2f}}<extra></extra>'
        ))
        
        # Add trend line
        z = np.polyfit(x_values, y_values, 1)
        p = np.poly1d(z)
        trend_x = np.array(x_values)
        trend_y = p(trend_x)
        fig.add_trace(go.Scatter(
            x=trend_x,
            y=trend_y,
            mode='lines',
            name=f'Trend (slope: {z[0]:.2f})',
            line=dict(dash='dash', color='#e74c3c'),
            hovertemplate=f'{x_label}: %{{x}}<br>Predicted {y_label}: %{{y:.2f}}<extra></extra>'
        ))
        
        fig.update_layout(
            title=dict(
                text=title,
                x=0.5,
                font=dict(size=20)
            ),
            xaxis_title=dict(text=x_label, font=dict(size=14)),
            yaxis_title=dict(text=y_label, font=dict(size=14)),
            hovermode='closest',
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="right",
                x=0.99
            ),
            margin=dict(t=100, l=80, r=80, b=80)
        )
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_title = title.lower().replace(' ', '_')
        filename = f'{self.output_dir}/scatter_{safe_title}_{timestamp}.html'
        fig.write_html(
            filename,
            include_plotlyjs='cdn',
            full_html=True,
            config={'displayModeBar': True, 'responsive': True}
        )
        
        return filename
    
    def generate_html_report(self, report_data, chart_files):
        """Generate HTML report with embedded interactive visualizations."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_file = f'{self.output_dir}/performance_report_{timestamp}.html'
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Performance Test Report - {timestamp}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f8f9fa; }}
                .container {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
                .header {{ 
                    text-align: center; 
                    margin-bottom: 40px;
                    background: #fff;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .metrics {{ 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin: 20px 0;
                }}
                .metric-box {{ 
                    padding: 25px; 
                    background: #fff; 
                    border-radius: 10px;
                    text-align: center;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    transition: transform 0.2s;
                }}
                .metric-box:hover {{
                    transform: translateY(-5px);
                }}
                .visualization {{ 
                    margin: 30px 0;
                    background: #fff;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .visualization iframe {{ 
                    width: 100%;
                    height: 500px;
                    border: none;
                    border-radius: 5px;
                }}
                .recommendations {{ margin: 30px 0; }}
                .recommendation {{ 
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 5px;
                    background: #fff;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .high {{ border-left: 4px solid #ff4444; }}
                .medium {{ border-left: 4px solid #ffbb33; }}
                .low {{ border-left: 4px solid #00C851; }}
                .system-info {{
                    background: #fff;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    margin-top: 30px;
                }}
                h1, h2, h3, h4 {{ color: #2c3e50; }}
                .success-rate {{
                    font-size: 24px;
                    font-weight: bold;
                    color: {self._get_success_rate_color(report_data)}
                }}
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
                        <p style="font-size: 24px;">{report_data['test_results']['tests_run']}</p>
                    </div>
                    <div class="metric-box">
                        <h3>Success Rate</h3>
                        <p class="success-rate">
                            {(report_data['test_results']['tests_run'] - 
                              report_data['test_results']['failures']) / 
                              report_data['test_results']['tests_run'] * 100:.1f}%
                        </p>
                    </div>
                    <div class="metric-box">
                        <h3>Failed Tests</h3>
                        <p style="font-size: 24px; color: #ff4444;">
                            {report_data['test_results']['failures']}
                        </p>
                    </div>
                </div>
                
                <div class="visualizations">
                    <h2>Performance Visualizations</h2>
                    {self._generate_chart_sections(chart_files)}
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
    
    def _generate_chart_sections(self, chart_files):
        """Generate HTML sections for interactive charts."""
        sections = []
        for chart_file in chart_files:
            filename = os.path.basename(chart_file)
            title = ' '.join(word.title() for word in filename.split('_')[:2])
            sections.append(f"""
                <div class="visualization">
                    <h3>{title}</h3>
                    <iframe src="{chart_file}"></iframe>
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
        return f"<ul style='list-style-type: none; padding: 0;'>{''.join(items)}</ul>"
    
    def _get_success_rate_color(self, report_data):
        """Get color for success rate based on percentage."""
        success_rate = ((report_data['test_results']['tests_run'] - 
                        report_data['test_results']['failures']) / 
                       report_data['test_results']['tests_run'] * 100)
        if success_rate >= 90:
            return '#00C851'  # Green
        elif success_rate >= 75:
            return '#ffbb33'  # Yellow
        else:
            return '#ff4444'  # Red 