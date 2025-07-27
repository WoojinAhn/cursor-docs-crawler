"""Error handling utilities and recovery mechanisms."""

import logging
import os
import signal
import sys
import traceback
from typing import Optional, Callable, Any
from functools import wraps
from datetime import datetime


class GracefulKiller:
    """Handle graceful shutdown on SIGINT and SIGTERM."""
    
    def __init__(self):
        self.kill_now = False
        signal.signal(signal.SIGINT, self._exit_gracefully)
        signal.signal(signal.SIGTERM, self._exit_gracefully)
        self.logger = logging.getLogger(__name__)
    
    def _exit_gracefully(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.kill_now = True


class ErrorRecovery:
    """Provides error recovery mechanisms for various operations."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        """Initialize error recovery.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries (exponential backoff)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.logger = logging.getLogger(__name__)
    
    def retry_with_backoff(self, operation: Callable, *args, **kwargs) -> Any:
        """Retry operation with exponential backoff.
        
        Args:
            operation: Function to retry
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Result of successful operation
            
        Raises:
            Exception: Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return operation(*args, **kwargs)
            
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.1f} seconds..."
                    )
                    
                    import time
                    time.sleep(delay)
                else:
                    self.logger.error(f"All {self.max_retries + 1} attempts failed")
        
        raise last_exception


def handle_disk_space_error(func):
    """Decorator to handle disk space errors."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except OSError as e:
            if e.errno == 28:  # No space left on device
                logger = logging.getLogger(__name__)
                logger.error("Disk space error detected. Attempting cleanup...")
                
                # Try to free up space
                cleanup_temp_files()
                
                # Try operation once more
                try:
                    return func(*args, **kwargs)
                except OSError:
                    logger.error("Operation failed even after cleanup")
                    raise DiskSpaceError("Insufficient disk space") from e
            else:
                raise
    return wrapper


def handle_memory_error(func):
    """Decorator to handle memory errors."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except MemoryError as e:
            logger = logging.getLogger(__name__)
            logger.error("Memory error detected. Attempting garbage collection...")
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Try operation once more with reduced parameters if possible
            try:
                # If function has batch_size parameter, reduce it
                if 'batch_size' in kwargs:
                    kwargs['batch_size'] = max(1, kwargs['batch_size'] // 2)
                    logger.info(f"Retrying with reduced batch size: {kwargs['batch_size']}")
                
                return func(*args, **kwargs)
            except MemoryError:
                logger.error("Operation failed even after memory cleanup")
                raise InsufficientMemoryError("Insufficient memory") from e
    return wrapper


def cleanup_temp_files():
    """Clean up temporary files to free disk space."""
    logger = logging.getLogger(__name__)
    
    try:
        import tempfile
        import shutil
        
        temp_dir = tempfile.gettempdir()
        
        # Clean up old temporary files
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.startswith('tmp') or file.startswith('temp'):
                    try:
                        file_path = os.path.join(root, file)
                        # Only delete files older than 1 hour
                        if os.path.getmtime(file_path) < (datetime.now().timestamp() - 3600):
                            os.remove(file_path)
                            logger.debug(f"Cleaned up temp file: {file_path}")
                    except Exception:
                        continue  # Skip files we can't delete
        
        logger.info("Temporary file cleanup completed")
        
    except Exception as e:
        logger.warning(f"Could not clean up temporary files: {e}")


def check_system_resources():
    """Check available system resources."""
    logger = logging.getLogger(__name__)
    
    try:
        import shutil
        import psutil
        
        # Check disk space
        total, used, free = shutil.disk_usage('.')
        free_gb = free / (1024**3)
        
        if free_gb < 1.0:  # Less than 1GB free
            logger.warning(f"Low disk space: {free_gb:.2f} GB available")
            if free_gb < 0.1:  # Less than 100MB
                raise DiskSpaceError(f"Critically low disk space: {free_gb:.2f} GB")
        
        # Check memory
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024**3)
        
        if available_gb < 0.5:  # Less than 500MB available
            logger.warning(f"Low memory: {available_gb:.2f} GB available")
            if available_gb < 0.1:  # Less than 100MB
                raise InsufficientMemoryError(f"Critically low memory: {available_gb:.2f} GB")
        
        logger.debug(f"System resources OK - Disk: {free_gb:.2f}GB, Memory: {available_gb:.2f}GB")
        
    except ImportError:
        logger.debug("psutil not available, skipping resource check")
    except Exception as e:
        logger.warning(f"Could not check system resources: {e}")


class CrawlerError(Exception):
    """Base exception for crawler errors."""
    pass


class NetworkError(CrawlerError):
    """Network-related errors."""
    pass


class ContentError(CrawlerError):
    """Content processing errors."""
    pass


class PDFGenerationError(CrawlerError):
    """PDF generation errors."""
    pass


class DiskSpaceError(CrawlerError):
    """Disk space errors."""
    pass


class InsufficientMemoryError(CrawlerError):
    """Memory errors."""
    pass


def log_exception(logger: logging.Logger, exception: Exception, context: str = ""):
    """Log exception with full traceback and context.
    
    Args:
        logger: Logger instance
        exception: Exception to log
        context: Additional context information
    """
    logger.error(f"Exception in {context}: {type(exception).__name__}: {str(exception)}")
    logger.debug(f"Full traceback:\n{traceback.format_exc()}")


def create_error_report(exception: Exception, context: str = "") -> str:
    """Create detailed error report.
    
    Args:
        exception: Exception that occurred
        context: Context where exception occurred
        
    Returns:
        Formatted error report string
    """
    report = []
    report.append("=" * 60)
    report.append("ERROR REPORT")
    report.append("=" * 60)
    report.append(f"Timestamp: {datetime.now().isoformat()}")
    report.append(f"Context: {context}")
    report.append(f"Exception Type: {type(exception).__name__}")
    report.append(f"Exception Message: {str(exception)}")
    report.append("")
    report.append("Traceback:")
    report.append(traceback.format_exc())
    report.append("=" * 60)
    
    return "\n".join(report)


def save_error_report(exception: Exception, context: str = "", filename: Optional[str] = None):
    """Save error report to file.
    
    Args:
        exception: Exception that occurred
        context: Context where exception occurred
        filename: Optional filename (auto-generated if None)
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"error_report_{timestamp}.txt"
    
    try:
        report = create_error_report(exception, context)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger = logging.getLogger(__name__)
        logger.info(f"Error report saved: {filename}")
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Could not save error report: {e}")


def setup_error_handling():
    """Set up global error handling."""
    def handle_exception(exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions."""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger = logging.getLogger(__name__)
        logger.critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        
        # Save error report
        save_error_report(exc_value, "Uncaught exception")
    
    sys.excepthook = handle_exception