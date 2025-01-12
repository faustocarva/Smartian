import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import f_oneway
import matplotlib.cm as cm
from matplotlib.colors import to_rgba
import matplotlib.colors as mcolors
from scipy import stats

class DataCollect():
    LLAMA3_70_COLOR = '#1f77b4'
    LLAMA3_8_COLOR = '#ff7f0e'
    GPTOMINI_COLOR = '#2ca02c'
    MIXTRAL_8X7B_COLOR = '#d62728'
    GEMINI_FLASH_COLOR = '#9467bd'
    
    METRICS_HEADER = 'model,temperature,file,total_files,total_files_with_invalid_json,total_seeds,total_duplicate_seeds,total_seeds_with_invalid_struct,total_args_in_seeds,total_invalid_args_in_seeds,total_functions_in_seeds,total_invalid_function_in_seeds'.split(',')
    COVERAGE_HEADER = 'contract,temperature,transaction_index,model,seed_file,totalExecutions,deployFailCount,coveredEdges,coveredInstructions,coveredDefUseChains,bugsFound'.split(',')
    B1_TOTAL_COV_HEADER = 'contract,toalInstructions,totalEdges'.split(',')
    
    def __init__(self) -> None:
        print("")

    def load_coverage_data(self, csv):
        df = pd.read_csv(csv, header=None, names=self.B1_TOTAL_COV_HEADER)
        return df
    
    def build_perf_score_seeds(self, csv):
        df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)

        # Find the global maximum value of total_seeds
        max_total_seeds = df['total_seeds'].max()
        
        df['valid_seeds'] = df['total_seeds'] - df['total_duplicate_seeds'] - df['total_seeds_with_invalid_struct']         
        df['valid_seeds'] = df['valid_seeds'].replace(0, pd.NA)

        df['duplicate_percentage'] = (df['total_duplicate_seeds'] / max_total_seeds) * 100
        df['invalid_struct_percentage'] = (df['total_seeds_with_invalid_struct'] / max_total_seeds) * 100
        
        df['duplicate_rate'] = (df['total_duplicate_seeds'] / max_total_seeds)
        df['invalid_struct_rate'] = df['total_seeds_with_invalid_struct'] / max_total_seeds

        df['penalty_factor'] = (1 - df['duplicate_rate'] - df['invalid_struct_rate']).clip(lower=0)
        
        df['performance_score'] = df['total_seeds'] * df['penalty_factor']
        
        min_score = df['performance_score'].min()
        max_score = df['performance_score'].max()
        df['normalized_performance_score'] = (
            (df['performance_score'] - min_score) / (max_score - min_score) * 100
        )
        
        return df                    

    def build_perf_score_seeds_args_funcs_2(self, csv):
        df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)

        # Find the global maximum values
        max_total_seeds = df['total_seeds'].max()
        max_total_args = df['total_args_in_seeds'].max()
        max_total_functions = df['total_functions_in_seeds'].max()

        # Calculate valid seeds
        df['valid_seeds'] = df['total_seeds'] - df['total_duplicate_seeds'] - df['total_seeds_with_invalid_struct']         
        df['valid_seeds'] = df['valid_seeds'].replace(0, pd.NA)

        # Calculate percentages for all metrics
        df['duplicate_percentage'] = (df['total_duplicate_seeds'] / max_total_seeds) * 100
        df['invalid_struct_percentage'] = (df['total_seeds_with_invalid_struct'] / max_total_seeds) * 100
        df['invalid_args_percentage'] = (df['total_invalid_args_in_seeds'] / max_total_args) * 100
        df['invalid_functions_percentage'] = (df['total_invalid_function_in_seeds'] / max_total_functions) * 100

        # Calculate rates for penalty factor
        df['duplicate_rate'] = df['total_duplicate_seeds'] / max_total_seeds
        df['invalid_struct_rate'] = df['total_seeds_with_invalid_struct'] / max_total_seeds
        df['invalid_args_rate'] = df['total_invalid_args_in_seeds'] / max_total_args
        df['invalid_functions_rate'] = df['total_invalid_function_in_seeds'] / max_total_functions

        # Calculate combined penalty factor including all metrics
        # df['penalty_factor'] = (1 - 0.4*df['duplicate_rate'] - 
        #                     0.4*df['invalid_struct_rate'] - 
        #                     0.1*df['invalid_args_rate'] - 
        #                     0.1*df['invalid_functions_rate']).clip(lower=0)

        df['penalty_factor'] = (1 - df['duplicate_rate'] - 
                            df['invalid_struct_rate']).clip(lower=0)

        df['performance_score'] = df['total_seeds'] * df['penalty_factor']

        # # Normalize performance score
        # min_score = df['performance_score'].min()
        # max_score = df['performance_score'].max()
        # df['normalized_performance_score'] = (
        #     (df['performance_score'] - min_score) / (max_score - min_score) * 100
        # )
        
        # [Previous code remains identical until performance_score calculation]
        df['performance_score'] = df['total_seeds'] * df['penalty_factor']

        # First, let's group experiments by model and temperature and calculate mean values
        grouped_df = df.groupby(['model', 'temperature']).agg({
            'performance_score': 'mean',
            'total_seeds': 'mean'  # We'll need this for relative performance calculation
        }).reset_index()

        # Calculate statistical measures using the grouped data
        mean_score = grouped_df['performance_score'].mean()
        std_score = grouped_df['performance_score'].std()
        
        # Calculate z-scores for grouped data
        grouped_df['z_score'] = (grouped_df['performance_score'] - mean_score) / std_score
        
        # Calculate relative performance against theoretical maximum for grouped data
        theoretical_max = df['total_seeds'].max()  # Using max from original data as theoretical maximum
        grouped_df['relative_performance'] = (grouped_df['performance_score'] / theoretical_max) * 100
        
        # Calculate percentile ranks for grouped results
        grouped_df['percentile_rank'] = grouped_df['performance_score'].rank(pct=True) * 100
        
        # Calculate confidence intervals using standard error of the mean from the original grouped data
        confidence_level = 0.95
        z_critical = stats.norm.ppf((1 + confidence_level) / 2)
        
        # Calculate standard error and confidence intervals for each group
        ci_data = []
        for (model, temp), group in df.groupby(['model', 'temperature']):
            n_experiments = len(group)
            group_std = group['performance_score'].std()
            std_error = group_std / np.sqrt(n_experiments)
            
            relative_std_error = (std_error / theoretical_max) * 100
            ci_lower = (group['performance_score'].mean() / theoretical_max * 100) - (z_critical * relative_std_error)
            ci_upper = (group['performance_score'].mean() / theoretical_max * 100) + (z_critical * relative_std_error)
            
            ci_data.append({
                'model': model,
                'temperature': temp,
                'ci_lower': ci_lower,
                'ci_upper': ci_upper
            })
        
        ci_df = pd.DataFrame(ci_data)
        grouped_df = grouped_df.merge(ci_df, on=['model', 'temperature'])
        
        # Calculate p-values for z-scores
        grouped_df['p_value'] = 2 * (1 - stats.norm.cdf(abs(grouped_df['z_score'])))
        
        # Generate statistical reports for each model and temperature combination
        reports = []
        for _, row in grouped_df.iterrows():
            n_experiments = len(df[(df['model'] == row['model']) & 
                                (df['temperature'] == row['temperature'])])
            
            significance_text = "significantly above average (p < 0.05)" if row['p_value'] < 0.05 else \
                            "not significantly different from average (p ≥ 0.05)"
            
            report = (
                f"Model {row['model']} at temperature {row['temperature']} "
                f"(averaged across {n_experiments} experiments) achieved a "
                f"relative performance of {row['relative_performance']:.1f}% "
                f"(95% CI: {row['ci_lower']:.1f}%-{row['ci_upper']:.1f}%), "
                f"placing it in the {row['percentile_rank']:.1f}th percentile "
                f"of all tested configurations. The z-score of {row['z_score']:.2f} "
                f"indicates the performance was {significance_text}."
            )
            reports.append(report)
        
        # Store reports and normalized scores in original DataFrame
        grouped_df['statistical_report'] = reports
        grouped_df['normalized_performance_score'] = stats.norm.cdf(grouped_df['z_score']) * 100
        
        # Print reports
        print("\nDetailed Statistical Analysis of Grouped Experiments:")
        print("=" * 80)
        for report in reports:
            print("\n" + report)
            print("-" * 80)
        
        # Merge the grouped statistics back into the original DataFrame
        df = df.merge(
            grouped_df[['model', 'temperature', 'normalized_performance_score', 'statistical_report']], 
            on=['model', 'temperature']
        )
        
        return df    
        
    def build_perf_score_seeds_args_funcs(self, csv):
            df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)

            # Find the global maximum values
            max_total_seeds = df['total_seeds'].max()
            max_total_args = df['total_args_in_seeds'].max()
            max_total_functions = df['total_functions_in_seeds'].max()

            # Calculate valid seeds
            df['valid_seeds'] = df['total_seeds'] - df['total_duplicate_seeds'] - df['total_seeds_with_invalid_struct']         
            df['valid_seeds'] = df['valid_seeds'].replace(0, pd.NA)

            # Calculate percentages for all metrics
            df['duplicate_percentage'] = (df['total_duplicate_seeds'] / max_total_seeds) * 100
            df['invalid_struct_percentage'] = (df['total_seeds_with_invalid_struct'] / max_total_seeds) * 100
            df['invalid_args_percentage'] = (df['total_invalid_args_in_seeds'] / max_total_args) * 100
            df['invalid_functions_percentage'] = (df['total_invalid_function_in_seeds'] / max_total_functions) * 100

            # Calculate rates for penalty factor
            df['duplicate_rate'] = df['total_duplicate_seeds'] / max_total_seeds
            df['invalid_struct_rate'] = df['total_seeds_with_invalid_struct'] / max_total_seeds
            df['invalid_args_rate'] = df['total_invalid_args_in_seeds'] / max_total_args
            df['invalid_functions_rate'] = df['total_invalid_function_in_seeds'] / max_total_functions

            # Calculate combined penalty factor including all metrics
            df['penalty_factor'] = (1 - 0.4*df['duplicate_rate'] - 
                                0.4*df['invalid_struct_rate'] - 
                                0.1*df['invalid_args_rate'] - 
                                0.1*df['invalid_functions_rate']).clip(lower=0)

            df['performance_score'] = df['total_seeds'] * df['penalty_factor']

            # Normalize performance score
            min_score = df['performance_score'].min()
            max_score = df['performance_score'].max()
            df['normalized_performance_score'] = (
                (df['performance_score'] - min_score) / (max_score - min_score) * 100
            )
            
            return df
        
    def total_files(self, csv):
        df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)
        
        df['valid_files'] = df['total_files'] - df['total_files_with_invalid_json']
        df['valid_files'] = df['valid_files'].replace(0, pd.NA)
                  
        result = (
            df.groupby(['model', 'temperature'])
            .apply(lambda group: pd.Series({
                'mean_files': round(group['valid_files'].mean())
            }))
            .reset_index()            
        )        
        plt.figure(figsize=(10, 6))

        for model in result['model'].unique():
            model_data = result[result['model'] == model]
            plt.plot(
                model_data['temperature'],
                model_data['mean_files'],
                label=f'{model}',
                marker='o',  # Add markers at each point
                linestyle='-',  # Solid line
                linewidth=2
            )

        # Labels and title
        plt.title('Mean total files generated by Model per Temperature', fontsize=16)
        plt.xlabel('Temperature', fontsize=14)
        plt.ylabel('Total files', fontsize=14)
        
        #plt.ylim(0, 58)        
        plt.xlim(0.0, 1.2)
        plt.grid(alpha=0.3)
        plt.legend(fontsize=12, loc='best')

        plt.tight_layout()
        plt.savefig('plot_total_files_by_model_temperature.pdf', bbox_inches="tight")        
        
    def total_seeds(self, csv):
        df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)
                
        max_total_seeds = df['total_seeds'].max()                
        result = (
            df.groupby(['model', 'temperature'])
            .apply(lambda group: pd.Series({
                'mean_seeds': round(group['total_seeds'].mean())
            }))
            .reset_index()            
        )        
        plt.figure(figsize=(10, 6))

        for model in result['model'].unique():
            model_data = result[result['model'] == model]
            plt.plot(
                model_data['temperature'],
                model_data['mean_seeds'],
                label=f'{model}',
                marker='o',  # Add markers at each point
                linestyle='-',  # Solid line
                linewidth=2
            )

        # Labels and title
        plt.title('Mean total seeds generated by Model per Temperature', fontsize=16)
        plt.xlabel('Temperature', fontsize=14)
        plt.ylabel('Total seeds', fontsize=14)
        
        plt.ylim(0, max_total_seeds)        
        plt.xlim(0.0, 1.2)
        plt.grid(alpha=0.3)
        plt.legend(fontsize=12, loc='best')

        plt.tight_layout()
        plt.savefig('plot_total_seeds_by_model_temperature.pdf', bbox_inches="tight")        
                
        ########################################################################################################
        
        df['valid_seeds'] = df['total_seeds'] - df['total_duplicate_seeds'] - df['total_seeds_with_invalid_struct']         
        df['valid_seeds'] = df['valid_seeds'].replace(0, pd.NA)
        
        result_by_model_temp = (
            df.groupby(['model', 'temperature'])
            .apply(lambda group: pd.Series({
                'mean_seeds': round(group['valid_seeds'].mean())
            }))
            .reset_index()
        )
        
        result_by_model = (
            df.groupby(['model'])
            .apply(lambda group: pd.Series({
                'mean_seeds': round(group['valid_seeds'].mean())
            }))
            .reset_index()
        )
        result_by_model = result_by_model.sort_values(by=['mean_seeds'], ascending=False)
        print(result_by_model)

        plt.figure(figsize=(10, 6))

        line_data = {}
        for model in result_by_model_temp['model'].unique():
            model_data_temp = result_by_model_temp[result_by_model_temp['model'] == model]
            line, =  plt.plot(
                model_data_temp['temperature'],
                model_data_temp['mean_seeds'],
                label=f'{model}',
                marker='o',
                linestyle='-',  # Solid line
                linewidth=2,
            )
            line_data[model] = {
                'line': line,
                'color': line.get_color()
            }

        # Plot data grouped by model only
        for model in result_by_model['model']:
            mean_seed = result_by_model[result_by_model['model'] == model]['mean_seeds'].values[0]
            plt.axhline(
                y=mean_seed,
                linestyle='--',
                color=line_data[model]['color']  
            )

        # Labels and title
        plt.title('Valid Generated Seeds per Model & Temperature', fontsize=16)
        plt.xlabel('Temperature', fontsize=14)
        plt.ylabel('Total Seeds', fontsize=14)
        
        plt.ylim(0, max_total_seeds)
        plt.xlim(0.0, 1.2)
        plt.grid(alpha=0.3)
        plt.legend(fontsize=10, loc='best')

        # Show plot
        plt.tight_layout()                
        
        plt.savefig('plot_total_efective_seeds_by_model_temperature.pdf', bbox_inches="tight")

    def total_seed_and_files(self, csv):
        # Read and process data
        df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)
        
        # Calculate means grouped by model and temperature
        grouped_df = df.groupby(['model', 'temperature']).agg({
            'total_files': 'mean',
            'total_files_with_invalid_json': 'mean',
            'total_seeds': 'mean',
            'total_duplicate_seeds': 'mean',
            'total_seeds_with_invalid_struct': 'mean'
            
        }).reset_index()

        # Calculate mean total_files - total_files_with_invalid_json
        grouped_df['valid_files_mean'] = grouped_df['total_files'] - grouped_df['total_files_with_invalid_json']
        grouped_df['valid_seeds'] = grouped_df['total_seeds'] - grouped_df['total_duplicate_seeds'] - grouped_df['total_seeds_with_invalid_struct']    
        
        # Set figure size
        fig, ax1 = plt.subplots(figsize=(10, 6))
        
        # Set style
        sns.set_style("whitegrid")
        
        # Create plot for total seeds
        models = grouped_df['model'].unique()
        markers = ['o', 's', '^', 'D', 'x']  # Different markers for each model
        
        # Define color palette
        color_palette = sns.color_palette("tab10", len(models))  # Use seaborn's tab10 palette
        
        handles1 = []
        labels1 = []
        handles2 = []
        labels2 = []
        
        for model, marker, color in zip(models, markers, color_palette):
            model_data = grouped_df[grouped_df['model'] == model]
            
            # Plot seeds vs temperature on primary y-axis
            line1, = ax1.plot(model_data['temperature'], 
                            model_data['valid_seeds'], 
                            marker=marker,
                            markersize=10,
                            linewidth=2,
                            color=color,  # Use color from palette
                            label=f"Valid Seeds - {model}")
            handles1.append(line1)
            labels1.append(f"{model}")
        
        # Customize primary y-axis
        ax1.set_xlabel('Temperature')
        ax1.set_ylabel('Total Valid Seeds', fontweight='bold')
        ax1.tick_params(axis='y')
        ax1.set_title('Valid Seeds and Valid Files vs Temperature by Model',  fontweight='bold', fontsize=12)
        
        # Create secondary y-axis for valid files mean
        ax2 = ax1.twinx()
        
        for model, marker, color in zip(models, markers, color_palette):
            model_data = grouped_df[grouped_df['model'] == model]
            
            # Create a slightly lighter version of the color for the dashed lines
            lighter_color = mcolors.to_rgba(color, alpha=0.6)  # Slightly lighter by adjusting the alpha
            
            # Plot valid files mean vs temperature on secondary y-axis with a lighter color
            line2, = ax2.plot(model_data['temperature'], 
                            model_data['valid_files_mean'], 
                            marker=marker,
                            markersize=10,
                            linewidth=2,
                            linestyle='--',  # Dashed line style
                            color=lighter_color,  # Slightly lighter color for dashed lines
                            label=f"Valid Files - {model}")
            # handles2.append(line2)
            # labels2.append(f"Valid Files - {model}")
        
        # Customize secondary y-axis
        ax2.set_ylabel('Total Valid Files', fontweight='bold')
        ax2.tick_params(axis='y')
        
        # Combine handles and labels for both axes, and sort by color
        handles = handles1 + handles2
        labels = labels1 + labels2
        
        # Sorting by color (lightness)
        sorted_handles_labels = sorted(zip(handles, labels), key=lambda x: x[0].get_color())
        sorted_handles, sorted_labels = zip(*sorted_handles_labels)
        
        # Add combined legend
        ax1.legend(sorted_handles, sorted_labels, bbox_to_anchor=(1.11, 1), loc='upper left')
        
        # Add annotations for line styles
        fig.text(0.97, 0.62,
                'Solid lines: Valid Seeds\nDashed lines: Valid Files',
                fontsize=10,
                ha='right',
                bbox=dict(facecolor='white',
                        alpha=0.9,
                        edgecolor='gray',
                        boxstyle='round,pad=0.5'))    
        
        # Adjust layout
        plt.tight_layout()
        plt.savefig('plot_total_files_seeds_by_model_temperature.pdf', bbox_inches="tight")             
        
        ########################################################################################################
        # Read and process data
        df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)        
        
        # Calculate means grouped by model and temperature
        grouped_df = df.groupby(['model', 'temperature']).agg({
            'total_files': 'mean',
            'total_files_with_invalid_json': 'mean',
            'total_seeds': 'mean',
            'total_duplicate_seeds': 'mean',
            'total_seeds_with_invalid_struct': 'mean'
        }).reset_index()

        # Calculate valid files and seeds
        grouped_df['valid_files_mean'] = grouped_df['total_files'] - grouped_df['total_files_with_invalid_json']
        grouped_df['valid_seeds'] = grouped_df['total_seeds'] - grouped_df['total_duplicate_seeds'] - grouped_df['total_seeds_with_invalid_struct']    
        
        # Create figure with shared y-axis
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
        
        models = grouped_df['model'].unique()
        markers = ['o', 'D', 's', '^', 'v']  # More distinct markers
        color_palette = sns.color_palette("tab10", len(models))  # Original color palette
        
        # First plot: Valid Seeds
        for model, marker, color in zip(models, markers, color_palette):
            model_data = grouped_df[grouped_df['model'] == model]
            line = ax1.plot(model_data['temperature'], 
                        model_data['valid_seeds'], 
                        marker=marker,
                        markersize=12,
                        linewidth=3,
                        color=color,
                        label=f"{model}",
                        alpha=0.8)
            
            # Add shadow effect to lines
            ax1.plot(model_data['temperature'], 
                    model_data['valid_seeds'],
                    color='gray',
                    linewidth=4,
                    alpha=0.2,
                    zorder=-1)
        
        ax1.set_xlabel('Temperature', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Total Valid Seeds', fontsize=12, fontweight='bold')
        ax1.set_title('Valid Seeds vs Temperature by Model', 
                    fontweight='bold', 
                    fontsize=14,
                    pad=20)
        ax1.grid(True, linestyle='--', alpha=0.7)
        ax1.tick_params(axis='both', which='major', labelsize=10)
        
        # Add light background color to first plot
        ax1.set_facecolor('#f8f9fa')
        
        # Second plot: Valid Files
        for model, marker, color in zip(models, markers, color_palette):
            model_data = grouped_df[grouped_df['model'] == model]
            line = ax2.plot(model_data['temperature'], 
                        model_data['valid_files_mean'], 
                        marker=marker,
                        markersize=12,
                        linewidth=3,
                        color=color,
                        label=f"{model}",
                        alpha=0.8)
            
            # Add shadow effect to lines
            ax2.plot(model_data['temperature'], 
                    model_data['valid_files_mean'],
                    color='gray',
                    linewidth=4,
                    alpha=0.2,
                    zorder=-1)
        
        ax2.set_xlabel('Temperature', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Total Valid Files', fontsize=12, fontweight='bold')
        ax2.set_title('Valid Files vs Temperature by Model', 
                    fontweight='bold', 
                    fontsize=14,
                    pad=20)
        ax2.grid(True, linestyle='--', alpha=0.7)
        ax2.tick_params(axis='both', which='major', labelsize=10)
        
        # Add light background color to second plot
        ax2.set_facecolor('#f8f9fa')
        
        # Enhance legend
        for ax in [ax1, ax2]:
            legend = ax.legend(bbox_to_anchor=(0.5, -0.15),
                            loc='upper center',
                            ncol=len(models),
                            fontsize=10,
                            frameon=True,
                            fancybox=True,
                            shadow=True)
            legend.get_frame().set_facecolor('white')
            legend.get_frame().set_alpha(0.9)
        
        # Add a super title
        fig.suptitle('Model Performance Analysis', 
                    fontsize=16, 
                    fontweight='bold', 
                    y=1.05)
        
        # Add subtle border around the entire figure
        for ax in [ax1, ax2]:
            for spine in ax.spines.values():
                spine.set_edgecolor('#cccccc')
                spine.set_linewidth(1.5)
        
        # Adjust layout
        plt.tight_layout()           
        plt.savefig('plot_total_files_seeds_by_model_side_temperature.pdf',bbox_inches="tight")                    

    def performance_score_all_metrics(self, csv):
        df = self.build_perf_score_seeds_args_funcs(csv)

        # Group by model and temperature
        result = (
            df.groupby(['model', 'temperature'])
            .apply(lambda group: pd.Series({
                'duplicate_percentage': group['duplicate_percentage'].mean(),
                'invalid_struct_percentage': group['invalid_struct_percentage'].mean(),
                'invalid_args_percentage': group['invalid_args_percentage'].mean(),
                'invalid_functions_percentage': group['invalid_functions_percentage'].mean(),
                'performance_score': group['normalized_performance_score'].mean(),
                'mean_valid_seeds': round(group['valid_seeds'].mean()),
                'mean_total_seeds': round(group['total_seeds'].mean()),
                'mean_valid_args': round((group['total_args_in_seeds'] - group['total_invalid_args_in_seeds']).mean()),
                'mean_valid_functions': round((group['total_functions_in_seeds'] - group['total_invalid_function_in_seeds']).mean())
            }))
            .reset_index()            
        )        

        # Group by model only
        result_model = (
            df.groupby(['model'])            
            .apply(lambda group: pd.Series({
                'duplicate_percentage': group['duplicate_percentage'].mean(),
                'invalid_struct_percentage': group['invalid_struct_percentage'].mean(),
                'invalid_args_percentage': group['invalid_args_percentage'].mean(),
                'invalid_functions_percentage': group['invalid_functions_percentage'].mean(),
                'performance_score': group['normalized_performance_score'].mean(),
                'mean_valid_seeds': round(group['valid_seeds'].mean()),
                'mean_total_seeds': round(group['total_seeds'].mean()),
                'mean_valid_args': round((group['total_args_in_seeds'] - group['total_invalid_args_in_seeds']).mean()),
                'mean_valid_functions': round((group['total_functions_in_seeds'] - group['total_invalid_function_in_seeds']).mean())
            }))
            .reset_index()            
        )        

        # Calculate unique percentage
        result['uniq_percentage'] = 100 - result["duplicate_percentage"]
        result_model['uniq_percentage'] = 100 - result_model["duplicate_percentage"]        

        # Sort by performance score
        result = result.sort_values(by=['performance_score'], ascending=False)
        print(result) 
        
    def performance_score_print_tables(self, csv):
        df = self.build_perf_score_seeds(csv)
        
        result = (
            df.groupby(['model', 'temperature'])
            .apply(lambda group: pd.Series({
                'duplicate_percentage': group['duplicate_percentage'].mean(),
                'invalid_struct_percentage': group['invalid_struct_percentage'].mean(),                
                'performance_score': group['normalized_performance_score'].mean(),
                'mean_valid_seeds': round(group['valid_seeds'].mean()),
                'mean_total_seeds': round(group['total_seeds'].mean())                
            }))
            .reset_index()            
        )        

        result_model = (
            df.groupby(['model'])            
            .apply(lambda group: pd.Series({
                'duplicate_percentage': group['duplicate_percentage'].mean(),
                'invalid_struct_percentage': group['invalid_struct_percentage'].mean(),                                
                'performance_score': group['normalized_performance_score'].mean(),
                'mean_valid_seeds': round(group['valid_seeds'].mean()),
                'mean_total_seeds': round(group['total_seeds'].mean())                                
            }))
            .reset_index()            
        )        
        
        result['uniq_percentage'] = 100 - result["duplicate_percentage"]
        result_model['uniq_percentage'] = 100 - result["duplicate_percentage"]        
        
        result = result.sort_values(by=['performance_score'], ascending=False)
        print(result)
        
        print("================================================================================================")
        
        result_model= result_model.sort_values(by=['performance_score'], ascending=False)
        print(result_model)
        
        print("================================================================================================")
        
        latex_table = result_model.to_latex(index=False)
        print(latex_table)
        print("================================================================================================") 
                
    def duplicate_cluster_quality_heat(self, csv):
        df = self.build_perf_score_seeds_args_funcs(csv)
        #df = self.build_perf_score_seeds(csv)

        # Aggregate data by model and temperature
        result = (
            df.groupby(['model', 'temperature'])
            .apply(lambda group: pd.Series({
                'performance_score': group['normalized_performance_score'].mean()
            }))
            .reset_index()
        )

        # Calculate the mean performance score for each model
        model_performance = result.groupby('model')['performance_score'].mean().reset_index()

        # Sort the models based on the mean performance score in descending order
        sorted_models = model_performance.sort_values(by='performance_score', ascending=False)['model']

        # Reorder the result DataFrame based on the sorted models
        result['model'] = pd.Categorical(result['model'], categories=sorted_models, ordered=True)

        # Pivot the data to create a matrix where rows are models and columns are temperatures
        heatmap_data = result.pivot(index='model', columns='temperature', values='performance_score')

        # Create a heatmap with Reds colormap
        plt.figure(figsize=(14, 8))

        # Use Seaborn's heatmap function with Reds colormap
        sns.heatmap(heatmap_data, annot=True, cmap='YlOrRd', fmt='.1f', linewidths=0.9)

        # Customize the plot
        plt.title('Seed Performance Score per Model and Temperature', fontsize=16)
        plt.xlabel('Temperature', fontsize=14)
        plt.ylabel('Model', fontsize=14)

        # Make y-axis labels horizontal and increase font size
        plt.yticks(rotation=0, fontsize=12)  # Set horizontal y labels with bigger font size

        # Show the plot
        plt.tight_layout()

        plt.savefig('performance_score_model_temp_heatmap.pdf', bbox_inches="tight")      
                  
    def metrics_info(self, csv):
        df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)
        
        grouped = (
            # Group by model
            df.groupby(['model'])            
            .apply(lambda group: pd.Series({
                'mean_seeds': group['total_seeds'].mean(),
                # 'mean_duplicate_seeds': group['total_duplicate_seeds'].mean(),
                # 'mean_seeds_with_invalid_struct': group['total_seeds_with_invalid_struct'].mean(),
                'mean_invalid_args_in_seeds_percentage': (group['total_invalid_args_in_seeds'].mean() / group['total_args_in_seeds'].mean() * 100) ,
                'mean_invalid_function_in_seeds_percentage': (group['total_invalid_function_in_seeds'].mean() / group['total_functions_in_seeds'].mean() * 100) ,
            }))
            .reset_index()
        )
                
        grouped = grouped.sort_values(by=['mean_invalid_function_in_seeds_percentage', 'mean_invalid_args_in_seeds_percentage'], ascending=False)
        pd.set_option('display.max_columns', None)  # Show all columns
        pd.set_option('display.width', 1000)       # Increase display width for better formatting

        # Print the result
        print(grouped)
         
    def valid(self, csv):
        df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)

        # Find the global maximum value of total_seeds
        max_total_seeds = df['total_seeds'].max()
        max_total_args_in_seeds = df['total_args_in_seeds'].max()
        max_total_functions_in_seeds = df['total_functions_in_seeds'].max()
        
        df['invalid_args_in_seeds'] = (df['total_invalid_args_in_seeds'] / max_total_args_in_seeds) * 100
        df['invalid_functions_in_seeds'] = (df['total_invalid_function_in_seeds'] / max_total_functions_in_seeds) * 100

        result = (
            #df.groupby(['model', 'temperature'])
            df.groupby(['model'])            
            .apply(lambda group: pd.Series({
                'invalid_args_in_seeds': group['invalid_args_in_seeds'].mean(),
                'invalid_functions_in_seeds': group['invalid_functions_in_seeds'].mean(),
            }))
            .reset_index()            
        )        
        
        result = result.sort_values(by=['model'], ascending=False)
        print(result)

    def coverage(self, csv):
        b1_csv = self.load_coverage_data("B1-ins.csv")
        total_instructions = b1_csv['toalInstructions'].sum()
        total_edges = b1_csv['totalEdges'].sum()

        df = pd.read_csv(csv, header=None, names=self.COVERAGE_HEADER)
                
        #df[['totalExecutions','deployFailCount','coveredEdges','coveredInstructions','coveredDefUseChains','bugsFound']] = df[['totalExecutions','deployFailCount','coveredEdges','coveredInstructions','coveredDefUseChains','bugsFound']].fillna(0)
        
        total_grp = df.groupby(['model', 'temperature', 'contract']).size().reset_index(name='row_count')
        print(total_grp.groupby(['model', 'temperature']).size().reset_index(name='seed_count').sort_values(by=['seed_count'], ascending=False))
        #print(df.groupby(['model', 'temperature', 'contract']).count())        
        
        #return
    
        average_covered_instructions = df.groupby(['model', 'temperature', 'contract'])['coveredInstructions'].mean().reset_index()
        total_inst_grouped = average_covered_instructions.groupby(['model', 'temperature'])['coveredInstructions'].sum().reset_index()
        total_inst_grouped.rename(columns={'coveredInstructions': 'totalCoveredInstructions'}, inplace=True)
        total_inst_grouped['totalCoveredInstructions_percentage'] = (total_inst_grouped['totalCoveredInstructions'] / total_instructions) * 100            
        total_inst_grouped = total_inst_grouped.sort_values(by=['totalCoveredInstructions_percentage'], ascending=False)
        print(total_inst_grouped)
        
        average_covered_edges = df.groupby(['model', 'temperature', 'contract'])['coveredEdges'].mean().reset_index()
        total_edges_grouped = average_covered_edges.groupby(['model', 'temperature'])['coveredEdges'].sum().reset_index()
        total_edges_grouped.rename(columns={'coveredEdges': 'totalCoveredEdges'}, inplace=True)
        total_edges_grouped['totalCoveredEdges_percentage'] = (total_edges_grouped['totalCoveredEdges'] / total_edges) * 100            
        total_edges_grouped = total_edges_grouped.sort_values(by=['totalCoveredEdges_percentage'], ascending=False)
        print(total_edges_grouped)
        
        return
        
        average_covered_instructions = df.groupby(['model', 'temperature'])['coveredInstructions'].mean().reset_index()
        average_covered_instructions.rename(columns={'coveredInstructions': 'averageCoveredInstructions'}, inplace=True)
        average_covered_instructions = average_covered_instructions.sort_values(by=['averageCoveredInstructions'], ascending=False)
        print(average_covered_instructions)

        average_covered_edges = df.groupby(['model', 'temperature'])['coveredEdges'].mean().reset_index()
        average_covered_edges.rename(columns={'coveredEdges': 'averageCoveredEdges'}, inplace=True)
        average_covered_edges = average_covered_edges.sort_values(by=['averageCoveredEdges'], ascending=False)
        print(average_covered_edges)
        
        average_defusechain = df.groupby(['model', 'temperature'])['coveredDefUseChains'].mean().reset_index()
        average_defusechain.rename(columns={'coveredDefUseChains': 'averageCoveredDefUseChains'}, inplace=True)
        average_defusechain = average_defusechain.sort_values(by=['averageCoveredDefUseChains'], ascending=False)
        print(average_defusechain)
        
        average_bugsfound = df.groupby(['model', 'temperature'])['bugsFound'].mean().reset_index()
        average_bugsfound.rename(columns={'bugsFound': 'averageBugsFound'}, inplace=True)
        average_bugsfound = average_bugsfound.sort_values(by=['averageBugsFound'], ascending=False)
        print(average_bugsfound)

        #total_fail = df.groupby(['model'])['deployFailCount'].mean().reset_index()
        total_fail = df.groupby(['model']).size().reset_index()
        print(total_fail)
        # total_fail.rename(columns={'deployFailCount': 'totaldeployFailCount'}, inplace=True)
        # total_fail = total_fail.sort_values(by=['totaldeployFailCount'], ascending=False)
        # print(total_fail)


        total_seeds_per_model = df.groupby('model')['seed_file'].count()
        print(total_seeds_per_model)
        # Find the model with the most seeds
        max_seeds = total_seeds_per_model.max()

        # Normalize the data based on the model with the most seeds
        df['normalizedCoveredEdges'] = df['coveredEdges'] / max_seeds
        df['normalizedCoveredInstructions'] = df['coveredInstructions'] / max_seeds
        df['normalizedBugsFound'] = df['bugsFound'] / max_seeds

        pd.set_option('display.max_columns', None)  # Show all columns
        pd.set_option('display.width', 1000)       # Increase display width for better formatting

        # Group by 'model' and calculate statistics for each model
        model_stats = df.groupby('model').agg({
            # 'normalizedCoveredEdges': ['mean', 'sum', 'std'],
            # 'normalizedCoveredInstructions': ['mean', 'sum', 'std'],
            # 'normalizedBugsFound': ['mean', 'sum', 'std'],
            'coveredEdges': ['mean', 'sum', 'std'],
            'coveredInstructions': ['mean', 'sum', 'std'],
            'bugsFound': ['mean', 'sum', 'std']
        }).reset_index()

        # Display the statistics for each model
        print(model_stats)
        
        
        # Filter rows where any coverage field has a non-zero value
        df_filtered = df[(df['coveredEdges'] > 0) | (df['coveredInstructions'] > 0) | (df['coveredDefUseChains'] > 0)]

        # Count the number of unique contracts for each model
        contracts_with_coverage = df_filtered.groupby('model')['contract'].nunique().sort_values(ascending=False)

        # Print the sorted list of models with the highest number of contracts with coverage
        print(contracts_with_coverage)        
        
        print("========================================")
        print("Model with most coveredEdges by contract")
        
        # Filter rows where coverage fields are greater than zero
        df_filtered = df[(df['coveredEdges'] > 0) | (df['coveredInstructions'] > 0) | (df['coveredDefUseChains'] > 0)]

        # Group by contract and find the best model based on coveredEdges
        best_models = df_filtered.groupby('contract').apply(
            lambda group: group.loc[group['coveredEdges'].idxmax()]
        )

        # Select only the relevant columns for the output (contract, best model, and coverage)
        best_models = best_models[['contract', 'model', 'coveredEdges']]

        # Sort by coveredEdges to display the best models first
        best_models = best_models.sort_values(by='coveredEdges', ascending=False)

        # Print the list of best models for each contract
        #print(best_models)        
        
        wins_count = best_models['model'].value_counts()

        # Sort by number of wins (descending order)
        wins_count = wins_count.sort_values(ascending=False)        
        print(wins_count)                


        print("========================================")
        print("Model with most mean coveredEdges by contract")
        
        # Filter rows where coverage fields are greater than zero
        df_filtered = df[(df['coveredEdges'] > 0) | (df['coveredInstructions'] > 0) | (df['coveredDefUseChains'] > 0)]

        # Group by contract and model, and calculate the mean coveredEdges for each group
        mean_coverage = df_filtered.groupby(['contract', 'model']).agg(
            mean_coveredEdges=('coveredEdges', 'mean'),
            mean_coveredInstructions=('coveredInstructions', 'mean'),
            mean_coveredDefUseChains=('coveredDefUseChains', 'mean')
        ).reset_index()

        # For each contract, find the model with the highest mean coveredEdges
        best_models = mean_coverage.loc[mean_coverage.groupby('contract')['mean_coveredEdges'].idxmax()]

        # Count the number of wins (i.e., the number of times a model is the best for a contract)
        wins_count = best_models['model'].value_counts()

        # Sort by number of wins (descending order)
        wins_count = wins_count.sort_values(ascending=False)

        # Print the sorted list of models by number of wins
        print(wins_count)                
        
        print("========================================")
        print("Model with most coveredInstructions by contract")
        
        # Filter rows where coverage fields are greater than zero
        df_filtered = df[(df['coveredEdges'] > 0) | (df['coveredInstructions'] > 0) | (df['coveredDefUseChains'] > 0)]

        # Group by contract and find the best model based on coveredEdges
        best_models = df_filtered.groupby('contract').apply(
            lambda group: group.loc[group['coveredInstructions'].idxmax()]
        )

        # Select only the relevant columns for the output (contract, best model, and coverage)
        best_models = best_models[['contract', 'model', 'coveredInstructions']]

        # Sort by coveredEdges to display the best models first
        best_models = best_models.sort_values(by='coveredInstructions', ascending=False)

        # Print the list of best models for each contract
        #print(best_models)        
        
        wins_count = best_models['model'].value_counts()

        # Sort by number of wins (descending order)
        wins_count = wins_count.sort_values(ascending=False)        
        print(wins_count)                

        print("========================================")        
        print("Model with mean most coveredInstructions by contract")        
        # Filter rows where coverage fields are greater than zero
        df_filtered = df[(df['coveredEdges'] > 0) | (df['coveredInstructions'] > 0) | (df['coveredDefUseChains'] > 0)]

        # Group by contract and model, and calculate the mean coveredEdges for each group
        mean_coverage = df_filtered.groupby(['contract', 'model']).agg(
            mean_coveredEdges=('coveredEdges', 'mean'),
            mean_coveredInstructions=('coveredInstructions', 'mean'),
            mean_coveredDefUseChains=('coveredDefUseChains', 'mean')
        ).reset_index()

        # For each contract, find the model with the highest mean coveredEdges
        best_models = mean_coverage.loc[mean_coverage.groupby('contract')['mean_coveredInstructions'].idxmax()]

        # Count the number of wins (i.e., the number of times a model is the best for a contract)
        wins_count = best_models['model'].value_counts()

        # Sort by number of wins (descending order)
        wins_count = wins_count.sort_values(ascending=False)

        # Print the sorted list of models by number of wins
        print(wins_count)                

        print("========================================")
        print("Model with most coveredDefUseChains by contract")
        
        # Filter rows where coverage fields are greater than zero
        df_filtered = df[(df['coveredEdges'] > 0) | (df['coveredInstructions'] > 0) | (df['coveredDefUseChains'] > 0)]

        # Group by contract and find the best model based on coveredEdges
        best_models = df_filtered.groupby('contract').apply(
            lambda group: group.loc[group['coveredDefUseChains'].idxmax()]
        )

        # Select only the relevant columns for the output (contract, best model, and coverage)
        best_models = best_models[['contract', 'model', 'coveredDefUseChains', 'temperature']]

        # Sort by coveredEdges to display the best models first
        best_models = best_models.sort_values(by='coveredDefUseChains', ascending=False)

        # Print the list of best models for each contract
        print(best_models)        
        
        wins_count = best_models['model'].value_counts()

        # Sort by number of wins (descending order)
        wins_count = wins_count.sort_values(ascending=False)        
        print(wins_count)                
        print("========================================")


        print("========================================")
        print("Model with most bugsFound by contract")
        
        # Filter rows where coverage fields are greater than zero
        df_filtered = df[(df['coveredEdges'] > 0) | (df['coveredInstructions'] > 0) | (df['coveredDefUseChains'] > 0) | (df['bugsFound'] > 0)]

        # Group by contract and find the best model based on coveredEdges
        best_models = df_filtered.groupby('contract').apply(
            lambda group: group.loc[group['bugsFound'].idxmax()]
        )

        # Select only the relevant columns for the output (contract, best model, and coverage)
        best_models = best_models[['contract', 'model', 'bugsFound', 'temperature']]

        # Sort by coveredEdges to display the best models first
        best_models = best_models.sort_values(by='bugsFound', ascending=False)

        # Print the list of best models for each contract
        print(best_models)        
        
        wins_count = best_models['model'].value_counts()

        # Sort by number of wins (descending order)
        wins_count = wins_count.sort_values(ascending=False)        
        print(wins_count)                
        print("========================================")



        print("================THE BEST OF THE BEST========================")
        # Group by temperature and model
        grouped = df.groupby(['temperature', 'model'])

        # Initialize an empty list to store the results
        results = []

        # Iterate through each group
        for (temperature, model), group in grouped:
            # Calculate the mean of coverage metrics for this group
            mean_covered_edges = group['coveredEdges'].mean()
            mean_covered_instructions = group['coveredInstructions'].mean()
            mean_covered_def_use_chains = group['coveredDefUseChains'].mean()
            total_seeds = group['seed_file'].count()

            # Calculate a score for this model-temperature combination
            score = (mean_covered_edges + mean_covered_instructions + mean_covered_def_use_chains) * total_seeds
            results.append({
                'temperature': temperature,
                'model': model,
                'total_seeds': total_seeds,
                'mean_coveredEdges': mean_covered_edges,
                'mean_coveredInstructions': mean_covered_instructions,
                'mean_coveredDefUseChains': mean_covered_def_use_chains,
                'score': score
            })

        # Convert the results to a DataFrame
        results_df = pd.DataFrame(results)
        
        print(results_df.sort_values(by=['score'], ascending=False))
        # Get the best model and temperature combination overall (highest score)
        best_model_temperature = results_df.loc[results_df['score'].idxmax()]

        # Output the best model and temperature
        print(best_model_temperature)        
        print("================THE BEST OF THE BEST========================")        
        
        metrics = ['coveredEdges', 'coveredInstructions', 'coveredDefUseChains']
        print("\nANOVA Results:")
        for metric in metrics:
            # Group data by model for each metric
            groups = [df[df['model'] == model][metric] for model in df['model'].unique()]
            f_stat, p_value = f_oneway(*groups)
            print(f"Metric: {metric}")
            print(f"  F-statistic: {f_stat:.4f}, p-value: {p_value}")
            if p_value < 0.05:
                print("  Result: Statistically significant differences (p < 0.05)")
            else:
                print("  Result: No statistically significant differences (p >= 0.05)")        
        
        merged_df = (
            average_covered_instructions
            .merge(average_covered_edges, on=['model', 'temperature'])
            .merge(average_defusechain, on=['model', 'temperature'])
            .merge(average_bugsfound, on=['model', 'temperature'])
        )        
        plt.figure(figsize=(12, 8))

        for model in merged_df['model'].unique():
            model_data = merged_df[merged_df['model'] == model]

            # Plot each metric as a separate line
            plt.plot(
                model_data['temperature'],
                model_data['averageCoveredInstructions'],
                label=f'{model} - Avg Covered Instructions',
                linestyle='-', marker='o', linewidth=2
            )
            plt.plot(
                model_data['temperature'],
                model_data['averageCoveredEdges'],
                label=f'{model} - Avg Covered Edges',
                linestyle='--', marker='x', linewidth=2
            )
            plt.plot(
                model_data['temperature'],
                model_data['averageCoveredDefUseChains'],
                label=f'{model} - Avg DefUseChains',
                linestyle='-.', marker='s', linewidth=2
            )
            plt.plot(
                model_data['temperature'],
                model_data['averageBugsFound'],
                label=f'{model} - Avg Bugs Found',
                linestyle=':', marker='^', linewidth=2
            )

        # Labels, title, and legend
        plt.xlabel('Temperature', fontsize=14)
        plt.ylabel('Metrics', fontsize=14)
        plt.title('Metrics vs Temperature (Line Plot)', fontsize=16)
        plt.grid(alpha=0.3)
        plt.legend(fontsize=10, loc='upper right', bbox_to_anchor=(1.3, 1))

        # Adjust layout and show plot
        plt.tight_layout()
        plt.savefig('scatter_plot_coverage.png', dpi=300)
        
    def coverage2(self, csv):
        df = pd.read_csv(csv, header=None, names=self.COVERAGE_HEADER)
        
        # Group and calculate averages for each metric
        average_covered_instructions = df.groupby(['model', 'temperature'])['coveredInstructions'].mean().reset_index()
        average_covered_instructions.rename(columns={'coveredInstructions': 'averageCoveredInstructions'}, inplace=True)
        average_covered_instructions = average_covered_instructions.sort_values(by=['model', 'temperature'])

        average_covered_edges = df.groupby(['model', 'temperature'])['coveredEdges'].mean().reset_index()
        average_covered_edges.rename(columns={'coveredEdges': 'averageCoveredEdges'}, inplace=True)
        average_covered_edges = average_covered_edges.sort_values(by=['model', 'temperature'])

        average_defusechain = df.groupby(['model', 'temperature'])['coveredDefUseChains'].mean().reset_index()
        average_defusechain.rename(columns={'coveredDefUseChains': 'averageCoveredDefUseChains'}, inplace=True)
        average_defusechain = average_defusechain.sort_values(by=['model', 'temperature'])

        average_bugsfound = df.groupby(['model', 'temperature'])['bugsFound'].mean().reset_index()
        average_bugsfound.rename(columns={'bugsFound': 'averageBugsFound'}, inplace=True)
        average_bugsfound = average_bugsfound.sort_values(by=['model', 'temperature'])

        # Merge all metrics into a single data frame
        merged_df = (
            average_covered_instructions
            .merge(average_covered_edges, on=['model', 'temperature'])
            .merge(average_defusechain, on=['model', 'temperature'])
            .merge(average_bugsfound, on=['model', 'temperature'])
        )

        # Melt the data for Seaborn compatibility
        melted_df = merged_df.melt(
            id_vars=['model', 'temperature'],
            value_vars=['averageCoveredInstructions', 'averageCoveredEdges', 'averageCoveredDefUseChains', 'averageBugsFound'],
            var_name='Metric',
            value_name='Value'
        )

        # Create the FacetGrid with shared y-axis
        g = sns.FacetGrid(
            melted_df, 
            col='model', 
            col_wrap=3, 
            sharey=True,  # Ensure y-axis is shared across all facets
            height=4, 
            aspect=1.5
        )
        g.map(sns.lineplot, 'temperature', 'Value', 'Metric', marker='o')

        # Customize the plot
        g.add_legend(title='Metrics')
        g.set_axis_labels('Temperature', 'Value')
        g.set_titles('Model: {col_name}')
        plt.subplots_adjust(top=0.9)
        g.fig.suptitle('Metrics Trends by Model and Temperature (Uniform Y-Axis)')

        # Optional: Add grid lines for easier comparison
        for ax in g.axes.flat:
            ax.grid(alpha=0.3)

        plt.savefig('scatter_plot_coverage_2.png', dpi=800)        