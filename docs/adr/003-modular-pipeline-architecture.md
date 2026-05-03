# ADR 003: Modular Pipeline Architecture Refactoring

## Status
Accepted

## Context
SRT2Web initially had a monolithic pipeline implementation in `core/unified_pipeline.py` (800+ lines) that was difficult to maintain, test, and extend. The pipeline mixed orchestration, state management, metrics collection, and error handling in a single class.

Key issues:
- Single file with 800+ lines handling multiple responsibilities
- Difficult to test individual pipeline stages
- Hard to add new processing strategies (sequential, parallel, async)
- Error handling was scattered throughout the pipeline
- State management coupled with orchestration logic
- Metrics collection mixed with business logic

## Decision
We decided to refactor the monolithic pipeline into a modular architecture with clear separation of concerns:

### Architecture Components

1. **Base Classes** (`core/pipeline/base.py`):
   - `PipelineData` - Dataclass for data flowing between modules
   - `BaseModule` - Abstract base class for all pipeline modules
   - `PipelineStrategy` - Abstract base for execution strategies
   - `MetricsTracker` - Metrics collection (decoupled from business logic)

2. **Strategy Pattern** (`core/pipeline/strategies.py`):
   - `SequentialStrategy` - Process chunks one after another
   - `ThreadParallelStrategy` - Process chunks in parallel using threads
   - `AsyncPipelineStrategy` - Async/await based processing

3. **Orchestration** (`core/pipeline_manager.py`):
   - `PipelineOrchestrator` - Central orchestrator that coordinates modules
   - Handles module lifecycle (start/stop)
   - Manages data flow between modules

4. **State Management** (`core/pipeline_state_manager.py`):
   - `PipelineStateManager` - Isolated state management
   - Tracks pipeline status, module states, metrics
   - Thread-safe operations

5. **Error Handling** (`core/pipeline_error_handler.py`):
   - `PipelineErrorHandler` - Centralized error handling
   - Retry logic with exponential backoff
   - Module-specific error recovery strategies
   - Error classification and reporting

6. **Factory** (`core/pipeline/factory.py`):
   - `PipelineFactory` - Creates pipeline instances based on configuration
   - Easy to switch between strategies

7. **Module Base** (`core/module_base.py`):
   - `BaseModule` - Enhanced base class for all modules
   - Standardized `get_status()`, `start()`, `stop()` methods
   - Signal-based communication between modules]

### Module Interfaces

```python
class BaseModule:
    """Base class for all pipeline modules."""
    
    def start(self) -> None:
        """Start the module."""
        ...
    
    def stop(self) -> None:
        """Stop the module."""
        ...
    
    def process(self, data: PipelineData) -> PipelineData:
        """Process input data and return output."""
        ...
    
    def get_status(self) -> ModuleStatus:
        """Return current module status."""
        ...
```

### Data Flow

```
InputSource → [AudioExtractor] → [Transcriber] → [Translator] → [SubtitleGenerator]
                                              ↓
                                    [TTSEngine] → [AudioMixer] → [VideoMuxer] → OutputSink
```

## Consequences]

### Positive
- **Maintainability**: Each component has a single responsibility
- **Testability**: Easy to unit test individual components
- **Extensibility**: New strategies can be added without modifying existing code
- **Observability**: Centralized metrics and error handling
- **Scalability**: Can easily add new execution strategies (distributed, GPU-aware, etc.)

### Negative
- **Complexity**: More files and classes to understand
- **Overhead**: More abstraction layers (though minimal)
- **Learning Curve**: New developers need to understand the architecture]

### Mitigations
- Comprehensive documentation in `docs/architecture.md`
- Clear module interfaces and docstrings
- Architecture diagrams (Mermaid) in documentation
- ADRs (this document) to explain decisions]

## References
- `docs/architecture.md` - Architecture overview with Mermaid diagrams
- `core/pipeline/` - Modular pipeline implementation
- `core/module_base.py` - Base module class
- `tests/unit/test_pipeline_*.py` - Pipeline tests

## Date
2026-04-14
