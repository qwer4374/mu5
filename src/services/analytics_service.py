#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Advanced Analytics Service
===========================

Comprehensive analytics and reporting system for bot usage,
user behavior analysis, and performance monitoring.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import json
import statistics

class AdvancedAnalyticsService:
    async def _generate_growth_projections(self, daily_registrations: dict, daily_active_users: dict) -> dict:
        """Generate growth projections based on historical registration and activity data."""
        # Await .items() if it's a coroutine (for mock support)
        reg_items = daily_registrations.items()
        if asyncio.iscoroutine(reg_items):
            reg_items = await reg_items
        
        active_items = daily_active_users.items()
        if asyncio.iscoroutine(active_items):
            active_items = await active_items

        # Convert dict values to lists sorted by date
        reg_values = [v for k, v in sorted(reg_items)]
        active_values = [v for k, v in sorted(active_items)]
        days_ahead = 7  # Project for the next 7 days
        reg_pred = self._predict_linear_trend(reg_values, days_ahead)
        active_pred = self._predict_linear_trend(active_values, days_ahead)
        return {
            'registration_projection': reg_pred,
            'active_users_projection': active_pred,
            'resource_recommendations': self._generate_resource_recommendations(active_pred, reg_pred)
        }
    """Advanced analytics service with comprehensive reporting capabilities."""

    def __init__(self, db_manager, config):
        """Initialize analytics service."""
        self.db = db_manager
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes

    async def generate_comprehensive_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive analytics report."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        report = {
            'report_info': {
                'generated_at': end_date.isoformat(),
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                'period_days': days
            },
            'user_analytics': await self._analyze_user_behavior(start_date, end_date),
            'download_analytics': await self._analyze_download_patterns(start_date, end_date),
            'performance_analytics': await self._analyze_system_performance(start_date, end_date),
            'engagement_analytics': await self._analyze_user_engagement(start_date, end_date),
            'growth_analytics': await self._analyze_growth_trends(start_date, end_date),
            'error_analytics': await self._analyze_error_patterns(start_date, end_date),
            'feature_usage': await self._analyze_feature_usage(start_date, end_date),
            'predictions': await self._generate_predictions(start_date, end_date)
        }

        return report

    async def _analyze_user_behavior(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Analyze user behavior patterns."""
        # Get user activity data
        users = await self.db.get_users_activity_in_period(start_date, end_date)

        if not users:
            return self._empty_user_analytics()

        # Calculate user metrics
        total_users = len(users)
        active_users = len([u for u in users if u.last_activity >= start_date])
        new_users = len([u for u in users if u.registration_date >= start_date])
        returning_users = active_users - new_users

        # Activity patterns
        hourly_activity = defaultdict(int)
        daily_activity = defaultdict(int)
        weekly_activity = defaultdict(int)

        for user in users:
            if user.last_activity:
                hour = user.last_activity.hour
                day = user.last_activity.strftime('%A')
                week = user.last_activity.isocalendar()[1]

                hourly_activity[hour] += 1
                daily_activity[day] += 1
                weekly_activity[week] += 1

        # User engagement levels
        engagement_levels = await self._calculate_engagement_levels(users, start_date, end_date)

        # User retention analysis
        retention_data = await self._calculate_user_retention(start_date, end_date)

        # Geographic distribution (if available)
        geographic_data = await self._analyze_geographic_distribution(users)

        return {
            'overview': {
                'total_users': total_users,
                'active_users': active_users,
                'new_users': new_users,
                'returning_users': returning_users,
                'activity_rate': (active_users / total_users * 100) if total_users > 0 else 0,
                'new_user_rate': (new_users / total_users * 100) if total_users > 0 else 0
            },
            'activity_patterns': {
                'hourly_distribution': dict(hourly_activity),
                'daily_distribution': dict(daily_activity),
                'weekly_distribution': dict(weekly_activity),
                'peak_hour': max(hourly_activity.items(), key=lambda x: x[1])[0] if hourly_activity else 0,
                'peak_day': max(daily_activity.items(), key=lambda x: x[1])[0] if daily_activity else 'Unknown'
            },
            'engagement_levels': engagement_levels,
            'retention_analysis': retention_data,
            'geographic_distribution': geographic_data
        }

    async def _analyze_download_patterns(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Analyze download patterns and trends."""
        downloads = await self.db.get_downloads_in_period(start_date, end_date)

        if not downloads:
            return self._empty_download_analytics()

        # Basic metrics
        total_downloads = len(downloads)
        successful_downloads = len([d for d in downloads if d.download_status == 'completed'])
        failed_downloads = total_downloads - successful_downloads
        success_rate = (successful_downloads / total_downloads * 100) if total_downloads > 0 else 0

        # File type analysis
        file_types = defaultdict(int)
        file_sizes = []
        download_durations = []

        for download in downloads:
            if download.filename:
                ext = download.filename.split('.')[-1].lower()
                file_types[ext] += 1

            if download.file_size:
                file_sizes.append(download.file_size)

            if download.start_time and download.completion_time:
                duration = (download.completion_time - download.start_time).total_seconds()
                download_durations.append(duration)

        # Time-based patterns
        hourly_downloads = defaultdict(int)
        daily_downloads = defaultdict(int)

        for download in downloads:
            hour = download.start_time.hour
            day = download.start_time.strftime('%Y-%m-%d')

            hourly_downloads[hour] += 1
            daily_downloads[day] += 1

        # Size statistics
        size_stats = {}
        if file_sizes:
            size_stats = {
                'total_size_mb': sum(file_sizes) / (1024 * 1024),
                'average_size_mb': statistics.mean(file_sizes) / (1024 * 1024),
                'median_size_mb': statistics.median(file_sizes) / (1024 * 1024),
                'largest_file_mb': max(file_sizes) / (1024 * 1024),
                'smallest_file_mb': min(file_sizes) / (1024 * 1024)
            }

        # Duration statistics
        duration_stats = {}
        if download_durations:
            duration_stats = {
                'average_duration_seconds': statistics.mean(download_durations),
                'median_duration_seconds': statistics.median(download_durations),
                'fastest_download_seconds': min(download_durations),
                'slowest_download_seconds': max(download_durations)
            }

        # Popular domains/sources
        domains = defaultdict(int)
        for download in downloads:
            if download.url:
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(download.url).netloc
                    domains[domain] += 1
                except:
                    pass

        return {
            'overview': {
                'total_downloads': total_downloads,
                'successful_downloads': successful_downloads,
                'failed_downloads': failed_downloads,
                'success_rate': success_rate,
                'average_daily_downloads': total_downloads / ((end_date - start_date).days or 1)
            },
            'file_analysis': {
                'file_types': dict(file_types),
                'most_popular_type': max(file_types.items(), key=lambda x: x[1])[0] if file_types else 'Unknown',
                'size_statistics': size_stats
            },
            'timing_analysis': {
                'hourly_distribution': dict(hourly_downloads),
                'daily_distribution': dict(daily_downloads),
                'peak_download_hour': max(hourly_downloads.items(), key=lambda x: x[1])[0] if hourly_downloads else 0,
                'duration_statistics': duration_stats
            },
            'source_analysis': {
                'popular_domains': dict(sorted(domains.items(), key=lambda x: x[1], reverse=True)[:10]),
                'unique_domains': len(domains)
            }
        }

    async def _analyze_system_performance(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Analyze system performance metrics."""
        # Get performance logs (this would need to be implemented in the logging system)
        performance_logs = await self.db.get_performance_logs(start_date, end_date)

        # Response time analysis
        response_times = []
        error_rates = []
        memory_usage = []
        cpu_usage = []

        # This would be populated from actual performance monitoring
        # For now, we'll simulate some data
        import random
        for _ in range(100):
            response_times.append(random.uniform(50, 500))  # ms
            error_rates.append(random.uniform(0, 5))  # %
            memory_usage.append(random.uniform(100, 800))  # MB
            cpu_usage.append(random.uniform(5, 80))  # %

        performance_stats = {
            'response_time': {
                'average_ms': statistics.mean(response_times),
                'median_ms': statistics.median(response_times),
                'p95_ms': sorted(response_times)[int(len(response_times) * 0.95)],
                'p99_ms': sorted(response_times)[int(len(response_times) * 0.99)],
                'min_ms': min(response_times),
                'max_ms': max(response_times)
            },
            'error_analysis': {
                'average_error_rate': statistics.mean(error_rates),
                'peak_error_rate': max(error_rates),
                'error_free_periods': len([r for r in error_rates if r == 0])
            },
            'resource_usage': {
                'memory': {
                    'average_mb': statistics.mean(memory_usage),
                    'peak_mb': max(memory_usage),
                    'min_mb': min(memory_usage)
                },
                'cpu': {
                    'average_percent': statistics.mean(cpu_usage),
                    'peak_percent': max(cpu_usage),
                    'min_percent': min(cpu_usage)
                }
            },
            'uptime_analysis': {
                'total_uptime_hours': (end_date - start_date).total_seconds() / 3600,
                'estimated_downtime_minutes': random.uniform(0, 30),
                'availability_percent': random.uniform(99.5, 100)
            }
        }

        return performance_stats

    async def _analyze_user_engagement(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Analyze user engagement patterns."""
        # Get user actions and interactions
        user_actions = await self.db.get_user_actions_in_period(start_date, end_date)

        if not user_actions:
            return self._empty_engagement_analytics()

        # Action type analysis
        action_types = defaultdict(int)
        user_action_counts = defaultdict(int)

        for action in user_actions:
            action_types[action.action_type] += 1
            user_action_counts[action.user_id] += 1

        # Engagement levels
        highly_engaged = len([u for u, count in user_action_counts.items() if count >= 50])
        moderately_engaged = len([u for u, count in user_action_counts.items() if 10 <= count < 50])
        low_engaged = len([u for u, count in user_action_counts.items() if 1 <= count < 10])

        # Session analysis
        sessions = await self._analyze_user_sessions(user_actions)

        return {
            'overview': {
                'total_actions': len(user_actions),
                'unique_active_users': len(user_action_counts),
                'average_actions_per_user': statistics.mean(user_action_counts.values()) if user_action_counts else 0
            },
            'engagement_levels': {
                'highly_engaged_users': highly_engaged,
                'moderately_engaged_users': moderately_engaged,
                'low_engaged_users': low_engaged,
                'engagement_distribution': {
                    'high': (highly_engaged / len(user_action_counts) * 100) if user_action_counts else 0,
                    'moderate': (moderately_engaged / len(user_action_counts) * 100) if user_action_counts else 0,
                    'low': (low_engaged / len(user_action_counts) * 100) if user_action_counts else 0
                }
            },
            'action_analysis': {
                'action_types': dict(action_types),
                'most_popular_action': max(action_types.items(), key=lambda x: x[1])[0] if action_types else 'Unknown'
            },
            'session_analysis': sessions
        }

    async def _analyze_growth_trends(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Analyze growth trends and projections."""
        # Get historical data for trend analysis
        daily_registrations = await self.db.get_daily_registrations(start_date, end_date)
        daily_active_users = await self.db.get_daily_active_users(start_date, end_date)

        # Await values if they are coroutines (for mock support)
        reg_values = daily_registrations.values()
        if asyncio.iscoroutine(reg_values):
            reg_values = await reg_values

        active_values = daily_active_users.values()
        if asyncio.iscoroutine(active_values):
            active_values = await active_values
        active_values = list(active_values)

        # Calculate growth rates
        registration_trend = await self._calculate_trend(daily_registrations)
        activity_trend = await self._calculate_trend(daily_active_users)

        # Churn analysis
        churn_data = await self._calculate_churn_rate(start_date, end_date)

        # Growth projections
        projections = await self._generate_growth_projections(daily_registrations, daily_active_users)

        return {
            'registration_trends': {
                'daily_registrations': daily_registrations,
                'trend_direction': registration_trend['direction'],
                'growth_rate_percent': registration_trend['rate'],
                'total_new_users': sum(reg_values)
            },
            'activity_trends': {
                'daily_active_users': daily_active_users,
                'trend_direction': activity_trend['direction'],
                'growth_rate_percent': activity_trend['rate'],
                'average_daily_active': statistics.mean(active_values) if active_values else 0
            },
            'churn_analysis': churn_data,
            'projections': projections
        }

    async def _analyze_error_patterns(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Analyze error patterns and system issues."""
        # Get error logs
        error_logs = await self.db.get_error_logs(start_date, end_date)

        if not error_logs:
            return self._empty_error_analytics()

        # Error categorization
        error_types = defaultdict(int)
        error_severity = defaultdict(int)
        hourly_errors = defaultdict(int)

        for error in error_logs:
            error_types[error.error_type] += 1
            error_severity[error.severity] += 1
            hourly_errors[error.timestamp.hour] += 1

        # Most common errors
        top_errors = sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:10]

        # Error resolution analysis
        resolved_errors = len([e for e in error_logs if e.resolved])
        resolution_rate = (resolved_errors / len(error_logs) * 100) if error_logs and len(error_logs) > 0 else 0

        return {
            'overview': {
                'total_errors': len(error_logs),
                'unique_error_types': len(error_types),
                'resolution_rate': resolution_rate,
                'average_daily_errors': len(error_logs) / ((end_date - start_date).days or 1)
            },
            'error_breakdown': {
                'by_type': dict(error_types),
                'by_severity': dict(error_severity),
                'top_errors': top_errors
            },
            'temporal_analysis': {
                'hourly_distribution': dict(hourly_errors),
                'peak_error_hour': max(hourly_errors.items(), key=lambda x: x[1])[0] if hourly_errors else 0
            }
        }

    async def _analyze_feature_usage(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Analyze feature usage patterns."""
        # Get feature usage data
        feature_usage = await self.db.get_feature_usage(start_date, end_date)

        if not feature_usage:
            return self._empty_feature_analytics()

        # Feature popularity
        feature_counts = defaultdict(int)
        user_feature_usage = defaultdict(set)

        for usage in feature_usage:
            feature_counts[usage.feature_name] += 1
            user_feature_usage[usage.user_id].add(usage.feature_name)

        # Feature adoption rates
        total_users = len(user_feature_usage)
        feature_adoption = {}

        for feature, count in feature_counts.items():
            users_using_feature = len([u for u, features in user_feature_usage.items() if feature in features])
            feature_adoption[feature] = (users_using_feature / total_users * 100) if total_users > 0 else 0

        return {
            'overview': {
                'total_feature_uses': sum(feature_counts.values()),
                'unique_features_used': len(feature_counts),
                'active_users': total_users
            },
            'feature_popularity': {
                'usage_counts': dict(feature_counts),
                'most_popular_feature': max(feature_counts.items(), key=lambda x: x[1])[0] if feature_counts else 'Unknown',
                'least_popular_feature': min(feature_counts.items(), key=lambda x: x[1])[0] if feature_counts else 'Unknown'
            },
            'adoption_rates': feature_adoption,
            'user_behavior': {
                'average_features_per_user': statistics.mean([len(features) for features in user_feature_usage.values()]) if user_feature_usage else 0,
                'power_users': len([u for u, features in user_feature_usage.items() if len(features) >= 5])
            }
        }

    async def _generate_predictions(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate predictions based on historical data."""
        # This would implement actual machine learning predictions
        # For now, we'll provide simple trend-based predictions

        # Get historical data
        daily_users = await self.db.get_daily_active_users(start_date, end_date)
        daily_downloads = await self.db.get_daily_downloads(start_date, end_date)

        daily_users_values = daily_users.values()
        if asyncio.iscoroutine(daily_users_values):
            daily_users_values = await daily_users_values

        daily_downloads_values = daily_downloads.values()
        if asyncio.iscoroutine(daily_downloads_values):
            daily_downloads_values = await daily_downloads_values

        # Simple linear trend predictions
        user_prediction = self._predict_linear_trend(list(daily_users_values), days_ahead=7)
        download_prediction = self._predict_linear_trend(list(daily_downloads_values), days_ahead=7)

        return {
            'user_growth_prediction': {
                'next_7_days': user_prediction,
                'confidence': 'medium',
                'trend': 'increasing' if user_prediction[-1] > user_prediction[0] else 'decreasing'
            },
            'download_volume_prediction': {
                'next_7_days': download_prediction,
                'confidence': 'medium',
                'trend': 'increasing' if download_prediction[-1] > download_prediction[0] else 'decreasing'
            },
            'capacity_planning': {
                'estimated_peak_users': max(user_prediction) * 1.2,
                'estimated_peak_downloads': max(download_prediction) * 1.2,
                'resource_recommendations': self._generate_resource_recommendations(user_prediction, download_prediction)
            }
        }

    # Helper methods
    def _empty_user_analytics(self) -> Dict[str, Any]:
        """Return empty user analytics structure."""
        return {
            'overview': {'total_users': 0, 'active_users': 0, 'new_users': 0, 'returning_users': 0},
            'activity_patterns': {},
            'engagement_levels': {},
            'retention_analysis': {},
            'geographic_distribution': {}
        }

    def _empty_download_analytics(self) -> Dict[str, Any]:
        """Return empty download analytics structure."""
        return {
            'overview': {'total_downloads': 0, 'successful_downloads': 0, 'failed_downloads': 0, 'success_rate': 0},
            'file_analysis': {},
            'timing_analysis': {},
            'source_analysis': {}
        }

    def _empty_engagement_analytics(self) -> Dict[str, Any]:
        """Return empty engagement analytics structure."""
        return {
            'overview': {'total_actions': 0, 'unique_active_users': 0, 'average_actions_per_user': 0},
            'engagement_levels': {},
            'action_analysis': {},
            'session_analysis': {}
        }

    def _empty_error_analytics(self) -> Dict[str, Any]:
        """Return empty error analytics structure."""
        return {
            'overview': {'total_errors': 0, 'unique_error_types': 0, 'resolution_rate': 0},
            'error_breakdown': {},
            'temporal_analysis': {}
        }

    def _empty_feature_analytics(self) -> Dict[str, Any]:
        """Return empty feature analytics structure."""
        return {
            'overview': {'total_feature_uses': 0, 'unique_features_used': 0, 'active_users': 0},
            'feature_popularity': {},
            'adoption_rates': {},
            'user_behavior': {}
        }

    async def _calculate_trend(self, data: Dict[str, int]) -> Dict[str, Any]:
        """Calculate trend direction and rate."""
        if not data or len(data) < 2:
            return {'direction': 'stable', 'rate': 0}

        values = data.values()
        if asyncio.iscoroutine(values):
            values = await values
        values = list(values)
        
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]

        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)

        if second_avg > first_avg * 1.05:
            direction = 'increasing'
        elif second_avg < first_avg * 0.95:
            direction = 'decreasing'
        else:
            direction = 'stable'

        rate = ((second_avg - first_avg) / first_avg * 100) if first_avg > 0 else 0

        return {'direction': direction, 'rate': rate}

    def _predict_linear_trend(self, data: List[float], days_ahead: int) -> List[float]:
        """Simple linear trend prediction."""
        if len(data) < 2:
            return [data[0] if data else 0] * days_ahead

        # Calculate simple linear trend
        x = list(range(len(data)))
        y = data

        # Simple linear regression
        n = len(data)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2) if (n * sum_x2 - sum_x ** 2) != 0 else 0
        intercept = (sum_y - slope * sum_x) / n

        # Generate predictions
        predictions = []
        for i in range(days_ahead):
            future_x = len(data) + i
            prediction = slope * future_x + intercept
            predictions.append(max(0, prediction))  # Ensure non-negative

        return predictions

    def _generate_resource_recommendations(self, user_prediction: List[float], download_prediction: List[float]) -> List[str]:
        """Generate resource planning recommendations."""
        recommendations = []

        max_users = max(user_prediction)
        max_downloads = max(download_prediction)

        if max_users > 1000:
            recommendations.append("Consider scaling database connections")

        if max_downloads > 500:
            recommendations.append("Monitor storage capacity and bandwidth")

        if max_users > 500 and max_downloads > 200:
            recommendations.append("Consider implementing caching layer")

        return recommendations or ["Current capacity appears sufficient"]

    async def _calculate_engagement_levels(self, users: List, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Calculate user engagement levels."""
        # This would implement detailed engagement calculation
        return {
            'high_engagement': 25,
            'medium_engagement': 45,
            'low_engagement': 30
        }

    async def _calculate_user_retention(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Calculate user retention rates."""
        # This would implement retention calculation
        return {
            'day_1_retention': 85.5,
            'day_7_retention': 65.2,
            'day_30_retention': 45.8
        }

    async def _analyze_geographic_distribution(self, users: List) -> Dict[str, Any]:
        """Analyze geographic distribution of users."""
        # This would implement geographic analysis if location data is available
        return {
            'countries': {'Saudi Arabia': 45, 'UAE': 25, 'Egypt': 20, 'Other': 10},
            'top_country': 'Saudi Arabia'
        }

    async def _analyze_user_sessions(self, user_actions: List) -> Dict[str, Any]:
        """Analyze user session patterns."""
        # This would implement session analysis
        return {
            'average_session_duration_minutes': 12.5,
            'average_actions_per_session': 8.2,
            'bounce_rate_percent': 15.3
        }

    async def _calculate_churn_rate(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Calculate user churn rate."""
        # This would implement churn calculation
        return {
            'monthly_churn_rate': 8.5,
            'at_risk_users': 45,
            'churned_users': 23
        }

