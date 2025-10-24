"""
批次時間切分收集器
自動將大時間範圍切分為小區間，避免 Apify 免費額度限制
"""
import sys
import os
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict
from dateutil.relativedelta import relativedelta
import time
import random

# 導入核心模組
from core.factory import CollectorFactory, register_all_collectors
from core.database_manager import create_database_manager_from_config
from core.data_models import HashtagCollectionResult

# 導入設定
from config.platform_config import (
    APIFY_TOKEN, MEDIA_FOLDER_PATH, SQL_CONFIGURE_PATH,
    MIN_DELAY, MAX_DELAY
)

# 導入日誌模組
from lib.logger import get_logger

# 建立 logger
logger = get_logger('BatchTimeCollector')


class TimeInterval:
    """時間區間類別"""

    @staticmethod
    def parse_date(date_str: str) -> datetime:
        """
        解析日期字串為 datetime 物件（帶時區資訊）

        支援格式:
        - YYYY-MM-DD (例: 2024-01-01)
        - YYYY-MM (例: 2024-01，自動補為當月第一天)
        - YYYY (例: 2024，自動補為當年第一天)

        參數:
            date_str: 日期字串

        返回:
            datetime 物件（帶 UTC 時區）
        """
        from datetime import timezone

        date_str = date_str.strip()

        # 嘗試不同的格式
        formats = [
            '%Y-%m-%d',  # 2024-01-01
            '%Y/%m/%d',  # 2024/01/01
            '%Y-%m',     # 2024-01
            '%Y/%m',     # 2024/01
            '%Y',        # 2024
        ]

        for fmt in formats:
            try:
                # 解析為 naive datetime，然後加上 UTC 時區
                naive_dt = datetime.strptime(date_str, fmt)
                # 加上 UTC 時區資訊
                return naive_dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

        raise ValueError(f"無法解析日期格式: {date_str}")

    @staticmethod
    def split_by_months(
        start_date: datetime,
        end_date: datetime,
        months_per_batch: int = 2
    ) -> List[Tuple[datetime, datetime]]:
        """
        按月份切分時間範圍

        參數:
            start_date: 起始日期
            end_date: 結束日期
            months_per_batch: 每個批次包含的月份數（預設2個月）

        返回:
            時間區間列表 [(start1, end1), (start2, end2), ...]
        """
        intervals = []
        current_start = start_date

        while current_start < end_date:
            # 計算當前批次的結束時間
            current_end = current_start + relativedelta(months=months_per_batch)

            # 如果超過總結束時間，則使用總結束時間
            if current_end > end_date:
                current_end = end_date

            intervals.append((current_start, current_end))

            # 移動到下一個批次的起始時間
            current_start = current_end

        return intervals

    @staticmethod
    def split_by_days(
        start_date: datetime,
        end_date: datetime,
        days_per_batch: int = 30
    ) -> List[Tuple[datetime, datetime]]:
        """
        按天數切分時間範圍

        參數:
            start_date: 起始日期
            end_date: 結束日期
            days_per_batch: 每個批次包含的天數（預設30天）

        返回:
            時間區間列表 [(start1, end1), (start2, end2), ...]
        """
        intervals = []
        current_start = start_date

        while current_start < end_date:
            # 計算當前批次的結束時間
            current_end = current_start + timedelta(days=days_per_batch)

            # 如果超過總結束時間，則使用總結束時間
            if current_end > end_date:
                current_end = end_date

            intervals.append((current_start, current_end))

            # 移動到下一個批次的起始時間
            current_start = current_end

        return intervals

    @staticmethod
    def split_by_years(
        start_date: datetime,
        end_date: datetime,
        years_per_batch: int = 1
    ) -> List[Tuple[datetime, datetime]]:
        """
        按年份切分時間範圍

        參數:
            start_date: 起始日期
            end_date: 結束日期
            years_per_batch: 每個批次包含的年份數（預設1年）

        返回:
            時間區間列表 [(start1, end1), (start2, end2), ...]
        """
        intervals = []
        current_start = start_date

        while current_start < end_date:
            # 計算當前批次的結束時間
            current_end = current_start + relativedelta(years=years_per_batch)

            # 如果超過總結束時間，則使用總結束時間
            if current_end > end_date:
                current_end = end_date

            intervals.append((current_start, current_end))

            # 移動到下一個批次的起始時間
            current_start = current_end

        return intervals


class BatchTimeCollector:
    """
    批次時間切分收集器

    功能:
    - 自動切分大時間範圍為小區間
    - 批次呼叫 hashtag 收集器
    - 避免 Apify 免費額度限制
    - 自動合併收集結果
    """

    def __init__(self):
        """初始化收集器"""
        # 註冊所有平台收集器
        register_all_collectors()

        # 建立資料庫管理器
        self.db = create_database_manager_from_config(SQL_CONFIGURE_PATH)

    def collect_hashtag_with_time_split(
        self,
        platform: str,
        hashtag: str,
        start_time: str,
        end_time: str,
        split_strategy: str = 'months',
        interval_size: int = 2,
        results_type: str = "posts",
        results_limit: int = 50,
        delay_between_batches: Tuple[int, int] = (10, 30)
    ) -> Dict:
        """
        收集指定 hashtag 的資料（自動時間切分）

        參數:
            platform: 平台名稱 (instagram, twitter, ...)
            hashtag: hashtag（可含或不含 # 符號）
            start_time: 起始時間 (格式: YYYY-MM-DD 或 YYYY-MM 或 YYYY)
            end_time: 結束時間 (格式: YYYY-MM-DD 或 YYYY-MM 或 YYYY)
            split_strategy: 切分策略 ('days', 'months', 'years')
            interval_size: 每個批次的區間大小
                - 'days': 天數 (例: 30 = 30天一批)
                - 'months': 月數 (例: 2 = 2個月一批)
                - 'years': 年數 (例: 1 = 1年一批)
            results_type: 結果類型 ("posts" 或 "reels")
            results_limit: 每個批次的結果數量限制
            delay_between_batches: 批次間的延遲時間範圍 (秒)，元組 (最小值, 最大值)

        返回:
            收集結果摘要字典
        """
        try:
            # 解析日期
            logger.info(f"{'='*60}")
            logger.info(f"批次時間切分收集 - {platform.upper()} #{hashtag}")
            logger.info(f"{'='*60}")
            logger.info(f"時間範圍: {start_time} ~ {end_time}")
            logger.info(f"切分策略: {split_strategy} (每批 {interval_size} 個單位)")
            logger.info(f"{'='*60}")

            start_date = TimeInterval.parse_date(start_time)
            end_date = TimeInterval.parse_date(end_time)

            # 驗證時間範圍
            if start_date >= end_date:
                error_msg = f"起始時間必須早於結束時間: {start_time} >= {end_time}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }

            # 切分時間區間
            if split_strategy == 'days':
                intervals = TimeInterval.split_by_days(start_date, end_date, interval_size)
            elif split_strategy == 'months':
                intervals = TimeInterval.split_by_months(start_date, end_date, interval_size)
            elif split_strategy == 'years':
                intervals = TimeInterval.split_by_years(start_date, end_date, interval_size)
            else:
                error_msg = f"不支援的切分策略: {split_strategy}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }

            logger.info(f"\n共切分為 {len(intervals)} 個批次:")
            for i, (interval_start, interval_end) in enumerate(intervals, 1):
                logger.info(f"  批次 {i}: {interval_start.strftime('%Y-%m-%d')} ~ {interval_end.strftime('%Y-%m-%d')}")

            # 逐批次收集
            all_results = []
            total_posts = 0
            success_batches = 0
            failed_batches = 0

            for i, (interval_start, interval_end) in enumerate(intervals, 1):
                logger.info(f"\n{'='*60}")
                logger.info(f"[批次 {i}/{len(intervals)}] 收集中...")
                logger.info(f"時間範圍: {interval_start.strftime('%Y-%m-%d')} ~ {interval_end.strftime('%Y-%m-%d')}")
                logger.info(f"{'='*60}")

                try:
                    # 執行收集（這裡需要傳遞時間範圍給收集器）
                    # 注意: Instagram Hashtag Scraper 本身不支援時間篩選
                    # 但我們仍然可以用時間切分來分散請求，避免一次抓取太多
                    result = self._collect_single_batch(
                        platform=platform,
                        hashtag=hashtag,
                        interval_start=interval_start,
                        interval_end=interval_end,
                        results_type=results_type,
                        results_limit=results_limit
                    )

                    if result.success:
                        all_results.append(result)
                        total_posts += len(result.posts)
                        success_batches += 1
                        logger.info(f"✓ 批次 {i} 成功: 收集了 {len(result.posts)} 個貼文")
                    else:
                        failed_batches += 1
                        logger.warning(f"✗ 批次 {i} 失敗: {result.error_message}")

                except Exception as e:
                    failed_batches += 1
                    logger.error(f"✗ 批次 {i} 發生錯誤: {e}")
                    import traceback
                    traceback.print_exc()

                # 批次間延遲（除了最後一個批次）
                if i < len(intervals):
                    delay = random.randint(delay_between_batches[0], delay_between_batches[1])
                    logger.info(f"[延遲] 等待 {delay} 秒後繼續下一批次...")
                    time.sleep(delay)

            # 返回收集摘要
            logger.info(f"\n{'='*60}")
            logger.info(f"批次收集完成！")
            logger.info(f"{'='*60}")
            logger.info(f"總批次數: {len(intervals)}")
            logger.info(f"成功批次: {success_batches}")
            logger.info(f"失敗批次: {failed_batches}")
            logger.info(f"總貼文數: {total_posts}")
            logger.info(f"{'='*60}")

            return {
                'success': True,
                'platform': platform,
                'hashtag': hashtag,
                'total_batches': len(intervals),
                'success_batches': success_batches,
                'failed_batches': failed_batches,
                'total_posts': total_posts,
                'results': all_results
            }

        except Exception as e:
            import traceback
            error_msg = f"批次收集失敗: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

    def _collect_single_batch(
        self,
        platform: str,
        hashtag: str,
        interval_start: datetime,
        interval_end: datetime,
        results_type: str,
        results_limit: int
    ) -> HashtagCollectionResult:
        """
        收集單一批次的資料

        參數:
            platform: 平台名稱
            hashtag: hashtag
            interval_start: 批次起始時間
            interval_end: 批次結束時間
            results_type: 結果類型
            results_limit: 結果數量限制

        返回:
            HashtagCollectionResult 物件
        """
        try:
            # 建立 hashtag 收集器
            collector = CollectorFactory.create_hashtag_collector(
                platform=platform,
                hashtag=hashtag,
                api_token=APIFY_TOKEN,
                results_type=results_type,
                results_limit=results_limit
            )

            if not collector:
                from core.data_models import PlatformType, HashtagCollectionResult
                return HashtagCollectionResult(
                    platform=PlatformType(platform.lower()),
                    hashtag=hashtag.lstrip('#'),
                    success=False,
                    error_message=f"無法建立 {platform} Hashtag 收集器"
                )

            # 執行收集（根據平台決定是否傳遞時間參數）
            if platform.lower() == 'twitter':
                # Twitter 支援原生時間過濾
                start_date_str = interval_start.strftime('%Y-%m-%d')
                end_date_str = interval_end.strftime('%Y-%m-%d')
                logger.info(f"  使用 Twitter 原生時間過濾: {start_date_str} ~ {end_date_str}")
                result = collector.collect_hashtag(
                    limit=results_limit,
                    start_date=start_date_str,
                    end_date=end_date_str
                )
            else:
                # 其他平台不支援原生時間過濾，收集後再過濾
                result = collector.collect_hashtag()

            # 過濾結果（只保留在時間範圍內的貼文）
            # Twitter 已在 API 層級過濾，其他平台需要手動過濾
            if result.success and result.posts and platform.lower() != 'twitter':
                from datetime import timezone

                original_count = len(result.posts)
                filtered_posts = []

                for post in result.posts:
                    if not post.created_at:
                        continue

                    # 確保 post.created_at 有時區資訊
                    post_created_at = post.created_at
                    if post_created_at.tzinfo is None:
                        # 如果沒有時區資訊，假設為 UTC
                        post_created_at = post_created_at.replace(tzinfo=timezone.utc)

                    # 比較時間（現在兩邊都有時區資訊）
                    if interval_start <= post_created_at < interval_end:
                        filtered_posts.append(post)

                result.posts = filtered_posts
                logger.info(f"  時間過濾: {original_count} -> {len(filtered_posts)} 個貼文")
            elif result.success and result.posts and platform.lower() == 'twitter':
                logger.info(f"  Twitter API 已過濾時間範圍，收集了 {len(result.posts)} 個貼文")

            # 下載媒體檔案
            if result.success and result.posts:
                logger.info(f"  下載 {len(result.posts)} 個貼文的媒體檔案...")
                for post in result.posts:
                    try:
                        collector.download_media(post, MEDIA_FOLDER_PATH)
                    except Exception as e:
                        logger.warning(f"  下載媒體失敗: {e}")

            # 儲存到資料庫
            if result.success and result.posts:
                self.db.save_hashtag_collection_result(result)

                # 儲存收集歷史記錄（加上時間範圍標記）
                username_with_time = f"hashtag_{result.hashtag}_{interval_start.strftime('%Y%m%d')}_{interval_end.strftime('%Y%m%d')}"
                self.db.save_collection_history(
                    platform=platform,
                    username=username_with_time,
                    success=result.success,
                    post_count=len(result.posts),
                    story_count=0,
                    error_message=result.error_message,
                    started_at=result.started_at,
                    finished_at=result.finished_at,
                    duration_seconds=result.duration_seconds
                )

            return result

        except Exception as e:
            import traceback
            error_msg = f"單一批次收集失敗: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)

            from core.data_models import PlatformType, HashtagCollectionResult
            return HashtagCollectionResult(
                platform=PlatformType(platform.lower()),
                hashtag=hashtag.lstrip('#'),
                success=False,
                error_message=error_msg
            )

    def close(self):
        """關閉資源"""
        self.db.close()
        logger.info("已關閉所有資源連接")


def main():
    """主程式入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description='批次時間切分收集器 - 自動切分大時間範圍為小區間',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  # 收集 2023 年全年的 hashtag，每 2 個月一批
  python batch_time_collector.py --platform instagram --hashtag travel \\
    --start-time 2023-01-01 --end-time 2024-01-01 \\
    --split-strategy months --interval-size 2

  # 收集 2022-2024 年的 hashtag，每 1 年一批
  python batch_time_collector.py --platform instagram --hashtag food \\
    --start-time 2022-01-01 --end-time 2025-01-01 \\
    --split-strategy years --interval-size 1

  # 收集最近 90 天的 hashtag，每 30 天一批
  python batch_time_collector.py --platform instagram --hashtag fitness \\
    --start-time 2024-10-01 --end-time 2024-12-31 \\
    --split-strategy days --interval-size 30

  # 收集 reels 類型，並設定每批次延遲
  python batch_time_collector.py --platform instagram --hashtag dance \\
    --start-time 2024-01-01 --end-time 2024-12-31 \\
    --split-strategy months --interval-size 1 \\
    --results-type reels --results-limit 100 \\
    --delay-min 15 --delay-max 45
        """
    )

    parser.add_argument('--platform', type=str, required=True,
                       help='平台名稱 (例: instagram, twitter)')
    parser.add_argument('--hashtag', type=str, required=True,
                       help='Hashtag（可含或不含 # 符號）')
    parser.add_argument('--start-time', type=str, required=True,
                       help='起始時間 (格式: YYYY-MM-DD 或 YYYY-MM 或 YYYY)')
    parser.add_argument('--end-time', type=str, required=True,
                       help='結束時間 (格式: YYYY-MM-DD 或 YYYY-MM 或 YYYY)')
    parser.add_argument('--split-strategy', type=str,
                       choices=['days', 'months', 'years'],
                       default='months',
                       help='切分策略 (預設: months)')
    parser.add_argument('--interval-size', type=int, default=2,
                       help='每個批次的區間大小 (預設: 2)')
    parser.add_argument('--results-type', type=str, default='posts',
                       choices=['posts', 'reels'],
                       help='結果類型 (預設: posts)')
    parser.add_argument('--results-limit', type=int, default=50,
                       help='每個批次的結果數量限制 (預設: 50)')
    parser.add_argument('--delay-min', type=int, default=10,
                       help='批次間最小延遲秒數 (預設: 10)')
    parser.add_argument('--delay-max', type=int, default=30,
                       help='批次間最大延遲秒數 (預設: 30)')

    args = parser.parse_args()

    # 建立收集器
    collector = BatchTimeCollector()

    try:
        # 執行批次收集
        result = collector.collect_hashtag_with_time_split(
            platform=args.platform,
            hashtag=args.hashtag,
            start_time=args.start_time,
            end_time=args.end_time,
            split_strategy=args.split_strategy,
            interval_size=args.interval_size,
            results_type=args.results_type,
            results_limit=args.results_limit,
            delay_between_batches=(args.delay_min, args.delay_max)
        )

        # 顯示結果
        if result['success']:
            logger.info("\n收集成功！")
            logger.info(f"總貼文數: {result['total_posts']}")
        else:
            logger.error(f"\n收集失敗: {result.get('error', 'Unknown error')}")

    finally:
        collector.close()


if __name__ == '__main__':
    main()
