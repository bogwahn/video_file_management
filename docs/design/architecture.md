# Architecture: video-file-management

## Vision

A suite of stackable, single-word CLI commands for creating and managing a video file library. The library spans multiple storage protocols (SMB, AFP, local) and will eventually serve files over multiple streaming protocols (HLS, DASH). Each command is a thin CLI wrapper over a composable domain layer.

## Principles

1. **Open Closed Principle** Objects should be open to extension and closed to modification.
2. **Single Responsibility Principle** There should never be more than one reason for a class to change
3. **Liskov Substitution Principle** Pointers or references to base classes must be able to use pointers or references of derived classes without knowing it.
4. **Interface Segregation Principle** Clients should not be forced to depend upon interface methods that they do not use
5. **Dependency Inversion Principle** Entities must depend on abstractions, not on concretions. High-level modules must not depend on low-level modules, both should depend on abstractions.
6. **Protocols first, ABCs second** Every extension point is a Protocol. ABCs can be used but only as an implementation of a Protocol.
7. **Commands own nothing.** Business logic lives in the domain. Commands are thin orchestrators.
8. **Readers read, writers write.** No class reads and writes. No reader knows about writers. No writer knows about readers.
9. **Errors are values.** No silent swallowing. No bare raises. Results carry errors as data.
10. **Storage is an abstraction.** Commands never touch the filesystem directly.
