"""
Web Scraping Example

Real-world scenario: Scraping data from JSONPlaceholder API with rate limiting,
caching, retry logic, and error handling.
"""

from src.http_client import (
    HTTPClient,
    HTTPClientConfig,
    RetryConfig,
    TimeoutConfig,
    CachePlugin,
    RateLimitPlugin,
    LoggingPlugin,
    MonitoringPlugin,
    HTTPClientException,
)
import logging
import time
from typing import List, Dict, Any


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class PostScraper:
    """Scraper for JSONPlaceholder posts."""

    def __init__(self):
        """Initialize scraper with optimized configuration."""

        # Configure client for scraping
        config = HTTPClientConfig(
            base_url="https://jsonplaceholder.typicode.com",
            headers={
                "User-Agent": "PostScraper/1.0 (Educational Example)",
                "Accept": "application/json",
            },

            # Timeouts
            timeout=TimeoutConfig(
                connect=5.0,
                read=10.0,
                total=30.0
            ),

            # Retry on failures
            retry=RetryConfig(
                max_attempts=3,
                backoff_factor=1.0,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["GET"]
            )
        )

        # Create client
        self.client = HTTPClient(config=config)

        # Add plugins
        self._setup_plugins()

    def _setup_plugins(self):
        """Configure plugins for scraping."""

        # Rate limiting: 5 requests per second (be nice to servers!)
        rate_limiter = RateLimitPlugin(max_calls=5, period=1.0)
        self.client.register_plugin(rate_limiter)

        # Caching: Cache responses for 5 minutes
        cache = CachePlugin(ttl=300, max_size=1000)
        self.client.register_plugin(cache)

        # Monitoring: Track performance
        self.monitor = MonitoringPlugin()
        self.client.register_plugin(self.monitor)

        # Logging
        log_plugin = LoggingPlugin(level=logging.INFO)
        self.client.register_plugin(log_plugin)

    def get_all_posts(self) -> List[Dict[str, Any]]:
        """Fetch all posts."""
        print("\n[1/4] Fetching all posts...")

        try:
            response = self.client.get("/posts")
            posts = response.json()
            print(f"  ✓ Found {len(posts)} posts")
            return posts

        except HTTPClientException as e:
            print(f"  ✗ Failed to fetch posts: {e}")
            return []

    def get_posts_by_user(self, user_id: int) -> List[Dict[str, Any]]:
        """Fetch posts by specific user."""
        print(f"\n[2/4] Fetching posts by user {user_id}...")

        try:
            response = self.client.get("/posts", params={"userId": user_id})
            posts = response.json()
            print(f"  ✓ User {user_id} has {len(posts)} posts")
            return posts

        except HTTPClientException as e:
            print(f"  ✗ Failed to fetch user posts: {e}")
            return []

    def get_post_with_comments(self, post_id: int) -> Dict[str, Any]:
        """Fetch post with its comments."""
        print(f"\n[3/4] Fetching post {post_id} with comments...")

        try:
            # Fetch post
            post_response = self.client.get(f"/posts/{post_id}")
            post = post_response.json()

            # Fetch comments
            comments_response = self.client.get(f"/posts/{post_id}/comments")
            comments = comments_response.json()

            post['comments'] = comments
            print(f"  ✓ Post {post_id}: '{post['title'][:50]}...'")
            print(f"  ✓ Has {len(comments)} comments")

            return post

        except HTTPClientException as e:
            print(f"  ✗ Failed to fetch post details: {e}")
            return {}

    def scrape_user_data(self, user_id: int) -> Dict[str, Any]:
        """Scrape all data for a specific user."""
        print(f"\n[4/4] Scraping complete data for user {user_id}...")

        user_data = {
            "user_id": user_id,
            "posts": [],
            "total_comments": 0
        }

        try:
            # Get user's posts
            posts = self.get_posts_by_user(user_id)

            # Get comments for each post
            for post in posts:
                try:
                    post_with_comments = self.get_post_with_comments(post['id'])
                    if post_with_comments:
                        user_data['posts'].append(post_with_comments)
                        user_data['total_comments'] += len(post_with_comments.get('comments', []))
                except Exception as e:
                    print(f"  ! Skipped post {post['id']}: {e}")

            print(f"\n  ✓ Scraped {len(user_data['posts'])} posts")
            print(f"  ✓ Total comments: {user_data['total_comments']}")

            return user_data

        except Exception as e:
            print(f"  ✗ Failed to scrape user data: {e}")
            return user_data

    def get_statistics(self) -> Dict[str, Any]:
        """Get scraping statistics."""
        metrics = self.monitor.get_metrics()

        return {
            "total_requests": metrics['total_requests'],
            "successful": metrics['successful_requests'],
            "failed": metrics['failed_requests'],
            "avg_response_time": f"{metrics['average_response_time']:.3f}s",
        }


def main():
    """Main scraping workflow."""
    print("=" * 60)
    print("Web Scraping Example - JSONPlaceholder")
    print("=" * 60)

    # Create scraper
    scraper = PostScraper()

    start_time = time.time()

    # 1. Get all posts overview
    all_posts = scraper.get_all_posts()

    # 2. Focus on specific user (user 1)
    user_posts = scraper.get_posts_by_user(user_id=1)

    # 3. Get detailed post with comments
    if all_posts:
        post_detail = scraper.get_post_with_comments(post_id=1)

    # 4. Scrape complete user data (be careful - this makes many requests!)
    # Uncomment to run full scrape:
    # user_data = scraper.scrape_user_data(user_id=1)

    elapsed = time.time() - start_time

    # Show statistics
    print("\n" + "=" * 60)
    print("Scraping Statistics")
    print("=" * 60)

    stats = scraper.get_statistics()
    print(f"Total requests: {stats['total_requests']}")
    print(f"Successful: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    print(f"Average response time: {stats['avg_response_time']}")
    print(f"Total time: {elapsed:.2f}s")

    print("\n" + "=" * 60)
    print("✓ Scraping completed successfully!")
    print("=" * 60)

    # Demonstrate cache effectiveness
    print("\n💡 Tips:")
    print("  • Rate limiting prevents overwhelming the server")
    print("  • Caching reduces duplicate requests")
    print("  • Retry logic handles temporary failures")
    print("  • Monitoring tracks performance metrics")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Scraping interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Scraping failed: {e}")
