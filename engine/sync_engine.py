"""Process synchronization simulation engine (discrete-event model)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


STATES = ("READY", "RUNNING", "WAITING", "BLOCKED", "TERMINATED")


class SyncSimulator:
    """Educational step-by-step synchronization simulations."""

    def __init__(self) -> None:
        self._algorithms = {
            "peterson": self._peterson,
            "dekker": self._dekker,
            "mutex": self._mutex,
            "binary_semaphore": self._binary_semaphore,
            "counting_semaphore": self._counting_semaphore,
            "producer_consumer": self._producer_consumer,
            "readers_writers": self._readers_writers,
            "monitor": self._monitor,
            "race_condition": self._race_condition,
            "deadlock_demo": self._deadlock_demo,
        }

    def list_algorithms(self) -> list[dict[str, str]]:
        meta = {
            "peterson": ("Peterson's Solution", "Two-process mutual exclusion without hardware locks."),
            "dekker": ("Dekker's Algorithm", "Classic two-process mutual exclusion."),
            "mutex": ("Mutex Lock", "Strict mutual exclusion via lock/unlock."),
            "binary_semaphore": ("Binary Semaphore", "P/V operations for mutual exclusion."),
            "counting_semaphore": ("Counting Semaphore", "Resource pool with limited slots."),
            "producer_consumer": ("Producer–Consumer", "Bounded buffer with semaphores."),
            "readers_writers": ("Readers–Writers", "Shared read, exclusive write."),
            "monitor": ("Monitor", "Condition variables inside a monitor."),
            "race_condition": ("Race Condition", "Unsafe shared counter vs corrected mutex."),
            "deadlock_demo": ("Deadlock Demo", "Circular wait leading to deadlock."),
        }
        return [
            {"id": k, "name": v[0], "description": v[1]}
            for k, v in meta.items()
        ]

    def run(self, algorithm: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
        config = config or {}
        if algorithm not in self._algorithms:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        steps, summary = self._algorithms[algorithm](config)
        return {
            "algorithm": algorithm,
            "config": config,
            "steps": steps,
            "summary": summary,
            "total_ticks": len(steps),
        }

    def _step(
        self,
        tick: int,
        processes: dict[str, str],
        action: str,
        message: str,
        *,
        critical_section: list[str] | None = None,
        waiting_queue: list[str] | None = None,
        resources: dict[str, Any] | None = None,
        shared_vars: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        # Copy every mutable argument: callers frequently pass live lists/dicts
        # (e.g. the readers' active list) that they keep mutating after this
        # step is recorded. Without copying, every recorded step would alias the
        # same object and end up showing its final state.
        return {
            "tick": tick,
            "processes": deepcopy(processes),
            "action": action,
            "message": message,
            "critical_section": list(critical_section) if critical_section else [],
            "waiting_queue": list(waiting_queue) if waiting_queue else [],
            "resources": deepcopy(resources) if resources else {},
            "shared_vars": deepcopy(shared_vars) if shared_vars else {},
        }

    def _peterson(self, config: dict) -> tuple[list, dict]:
        """
        Peterson's Solution — software mutual exclusion for 2 processes.

        Each process sets flag[i]=True (I want CS) and turn=other (you go first).
        Entry condition: wait while flag[other]==True AND turn==other.
        This guarantees mutual exclusion, progress, and bounded waiting.

        To show contention, both processes set their flags before either enters CS.
        """
        iterations = int(config.get("iterations", 3))
        steps: list[dict] = []
        tick = 0
        flag = [False, False]
        turn = 0
        counter = 0
        procs = {"P0": "READY", "P1": "READY"}

        def emit(action: str, msg: str, cs: list[str], wq: list[str]) -> None:
            nonlocal tick
            steps.append(
                self._step(
                    tick, procs, action, msg,
                    critical_section=cs, waiting_queue=wq,
                    shared_vars={"flag": flag[:], "turn": turn, "counter": counter},
                )
            )
            tick += 1

        emit("init", "Peterson: flag=[False,False], turn=0. Both processes will compete for CS.", [], [])

        for iteration in range(iterations):
            # Both processes signal intent simultaneously (shows contention)
            flag[0] = True
            flag[1] = True
            procs["P0"] = "RUNNING"
            procs["P1"] = "RUNNING"
            emit("request_cs", f"Iteration {iteration+1}: P0 and P1 both set flag=True (both want CS)", [], ["P0", "P1"])

            # P0 sets turn=1 (defers to P1), P1 sets turn=0 (defers to P0)
            # Last write wins — turn ends up as 0 (P1 wrote last, giving turn to P0)
            turn = 1   # P0 sets turn=1
            emit("set_turn", "P0: turn=1 (I defer to P1)", [], ["P0", "P1"])
            turn = 0   # P1 sets turn=0 (last write wins)
            emit("set_turn", "P1: turn=0 (I defer to P0) — last write wins, turn=0", [], ["P0", "P1"])

            # P1 must wait: flag[0]==True AND turn==0
            procs["P1"] = "WAITING"
            emit("wait", "P1 waits: flag[0]=True AND turn==0 → busy-wait", [], ["P1"])

            # P0 can enter: flag[1]==True but turn==0 (not 0's turn to defer)
            procs["P0"] = "RUNNING"
            emit("enter_cs", "P0 enters CS: flag[1]=True but turn=0 ≠ 1, so P0 proceeds", ["P0"], ["P1"])
            counter += 1
            emit("critical_section", f"P0 in CS — counter={counter}", ["P0"], ["P1"])

            # P0 exits CS
            flag[0] = False
            procs["P0"] = "READY"
            emit("exit_cs", "P0: flag[0]=False — releases CS", [], ["P1"])

            # P1 can now enter: flag[0]==False, busy-wait condition false
            procs["P1"] = "RUNNING"
            emit("enter_cs", "P1 enters CS: flag[0]=False → busy-wait exits", ["P1"], [])
            counter += 1
            emit("critical_section", f"P1 in CS — counter={counter}", ["P1"], [])

            # P1 exits CS
            flag[1] = False
            turn = 1
            procs["P1"] = "READY"
            emit("exit_cs", "P1: flag[1]=False, turn=1 — releases CS", [], [])

        procs = {k: "TERMINATED" for k in procs}
        emit("done", f"Peterson complete. counter={counter} (expected {iterations*2}). Mutual exclusion maintained.", [], [])
        return steps, {"final_counter": counter, "mutual_exclusion": True, "deadlock_free": True}

    def _dekker(self, config: dict) -> tuple[list, dict]:
        """
        Dekker's Algorithm — first software solution for mutual exclusion (2 processes).

        Each process sets its flag to signal intent.
        If both want CS, the one whose turn it is NOT defers:
          - clears its flag, busy-waits until it's its turn, then retries.
        After exiting CS, the process gives turn to the other.

        The simulation interleaves P0 and P1 step-by-step so that the deferral
        path is actually exercised: on odd iterations turn favours P0, on even
        iterations turn favours P1, so each process must defer once.
        """
        iterations = int(config.get("iterations", 3))
        steps: list[dict] = []
        tick = 0
        flag = [False, False]
        turn = 0          # whose turn it is to enter CS when both want it
        counter = 0
        procs = {"P0": "READY", "P1": "READY"}

        def emit(action: str, msg: str, cs: list[str], wq: list[str]) -> None:
            nonlocal tick
            steps.append(
                self._step(
                    tick, procs, action, msg,
                    critical_section=cs, waiting_queue=wq,
                    shared_vars={"flag": flag[:], "turn": turn, "counter": counter},
                )
            )
            tick += 1

        emit("init", "Dekker: flag=[False,False], turn=0. Both processes will compete simultaneously each iteration.", [], [])

        for iteration in range(iterations):
            # --- Step 1: both signal intent simultaneously (shows contention) ---
            flag[0] = True
            flag[1] = True
            procs["P0"] = "RUNNING"
            procs["P1"] = "RUNNING"
            emit(
                "flag_on",
                f"Iteration {iteration+1}: P0 sets flag[0]=True, P1 sets flag[1]=True — both want CS simultaneously.",
                [], [],
            )

            # --- Step 2: both check the other's flag — both see True → contention ---
            emit(
                "contend",
                f"P0 checks flag[1]=True; P1 checks flag[0]=True — contention detected. "
                f"turn={turn}: P{turn} may enter, P{1-turn} must defer.",
                [], [],
            )

            # The process whose turn it is NOT defers (clears flag, busy-waits)
            defer_pid = 1 - turn        # this process must defer
            enter_pid = turn            # this process may enter immediately

            # --- Step 3: deferring process clears its flag and busy-waits ---
            flag[defer_pid] = False
            procs[f"P{defer_pid}"] = "WAITING"
            emit(
                "defer",
                f"P{defer_pid}: turn={turn} ≠ {defer_pid} → NOT my turn. "
                f"P{defer_pid} clears flag[{defer_pid}]=False and enters busy-wait.",
                [], [f"P{defer_pid}"],
            )
            emit(
                "busy_wait",
                f"P{defer_pid}: busy-waiting for turn=={defer_pid} (currently turn={turn}). "
                f"CPU cycles consumed while waiting.",
                [], [f"P{defer_pid}"],
            )

            # --- Step 4: favoured process sees flag[other]=False → enters CS ---
            procs[f"P{enter_pid}"] = "RUNNING"
            emit(
                "enter_cs",
                f"P{enter_pid}: flag[{defer_pid}]=False (deferred) AND turn={turn}=={enter_pid} → enters CS.",
                [f"P{enter_pid}"], [f"P{defer_pid}"],
            )
            counter += 1
            emit(
                "critical_section",
                f"P{enter_pid} in CS — counter={counter}. P{defer_pid} still busy-waiting.",
                [f"P{enter_pid}"], [f"P{defer_pid}"],
            )

            # --- Step 5: favoured process exits CS, clears flag, passes turn ---
            flag[enter_pid] = False
            turn = defer_pid            # give turn to the process that deferred
            procs[f"P{enter_pid}"] = "READY"
            emit(
                "exit_cs",
                f"P{enter_pid} exits CS: flag[{enter_pid}]=False, turn={turn} "
                f"(turn given to P{turn} that was waiting).",
                [], [f"P{defer_pid}"],
            )

            # --- Step 6: deferred process sees turn changed → retries ---
            emit(
                "retry",
                f"P{defer_pid}: turn=={defer_pid} now! Retries: sets flag[{defer_pid}]=True.",
                [], [f"P{defer_pid}"],
            )
            flag[defer_pid] = True
            procs[f"P{defer_pid}"] = "RUNNING"

            # flag[enter_pid] is now False → deferred process can enter
            emit(
                "enter_cs",
                f"P{defer_pid}: checks flag[{enter_pid}]=False → busy-wait exits. Enters CS.",
                [f"P{defer_pid}"], [],
            )
            counter += 1
            emit(
                "critical_section",
                f"P{defer_pid} in CS — counter={counter}.",
                [f"P{defer_pid}"], [],
            )

            # --- Step 7: deferred process exits, passes turn back ---
            flag[defer_pid] = False
            turn = enter_pid
            procs[f"P{defer_pid}"] = "READY"
            emit(
                "exit_cs",
                f"P{defer_pid} exits CS: flag[{defer_pid}]=False, turn={turn}.",
                [], [],
            )

        procs = {k: "TERMINATED" for k in procs}
        emit(
            "done",
            f"Dekker complete. counter={counter} (expected {iterations*2}). "
            f"Deferral exercised every iteration — mutual exclusion maintained.",
            [], [],
        )
        return steps, {"final_counter": counter, "mutual_exclusion": True}

    def _mutex(self, config: dict) -> tuple[list, dict]:
        """
        Mutex lock simulation.

        acquire(): if unlocked → lock and enter CS; else → block.
        release(): if waiters → wake one; else → unlock.
        Processes run sequentially; each releases before the next acquires.
        """
        n = int(config.get("processes", 3))
        iterations = int(config.get("iterations", 2))
        steps: list[dict] = []
        tick = 0
        lock = False
        counter = 0
        procs = {f"P{i}": "READY" for i in range(n)}
        queue: list[str] = []

        def emit(action: str, msg: str, cs: list[str]) -> None:
            nonlocal tick
            steps.append(
                self._step(
                    tick, procs, action, msg,
                    critical_section=cs, waiting_queue=list(queue),
                    resources={"mutex_locked": lock},
                    shared_vars={"counter": counter},
                )
            )
            tick += 1

        emit("init", "Mutex lock available (unlocked)", [])

        for _ in range(iterations):
            for pid in sorted(procs.keys()):
                procs[pid] = "RUNNING"
                emit("request_lock", f"{pid} calls acquire(mutex)", [])

                if lock:
                    # Mutex is held — block this process
                    procs[pid] = "BLOCKED"
                    queue.append(pid)
                    emit("blocked", f"{pid} blocked — mutex held by another process", [])
                    # In sequential sim: previous holder already released, so unblock now
                    queue.remove(pid)
                    procs[pid] = "RUNNING"
                    emit("unblocked", f"{pid} unblocked — mutex now available", [])

                # Acquire the mutex
                lock = True
                emit("acquire", f"{pid} acquired mutex — lock=True", [pid])

                # Critical section
                counter += 1
                emit("critical_section", f"{pid} in CS — counter={counter}", [pid])

                # Release the mutex
                lock = False
                procs[pid] = "READY"
                if queue:
                    emit("release", f"{pid} released mutex — waking {queue[0]}", [])
                else:
                    emit("release", f"{pid} released mutex — lock=False", [])

        for pid in procs:
            procs[pid] = "TERMINATED"
        emit("done", f"Mutex simulation done. counter={counter}", [])
        return steps, {"final_counter": counter, "mutual_exclusion": True}

    def _binary_semaphore(self, config: dict) -> tuple[list, dict]:
        return self._semaphore_impl(config, initial=1, name="Binary Semaphore")

    def _counting_semaphore(self, config: dict) -> tuple[list, dict]:
        slots = int(config.get("slots", 2))
        return self._semaphore_impl(config, initial=slots, name="Counting Semaphore")

    def _semaphore_impl(self, config: dict, initial: int, name: str) -> tuple[list, dict]:
        """
        Correct P()/V() semaphore simulation.

        P(s): if s > 0 → s -= 1 and proceed; else → block until V() wakes you.
        V(s): if waiting queue non-empty → wake one; else → s += 1.

        Delegates to the contention model, where blocked processes wake only
        after another process executes V().
        """
        return self._semaphore_contention_impl(config, initial, name)

    def _semaphore_contention_impl(self, config: dict, initial: int, name: str) -> tuple[list, dict]:
        """P/V semaphore model where blocked processes wake only after V()."""
        n = int(config.get("processes", 4))
        iterations = int(config.get("iterations", 2))
        steps: list[dict] = []
        tick = 0
        sem = initial
        counter = 0
        procs = {f"P{i}": "READY" for i in range(n)}
        queue: list[str] = []

        def emit(action: str, msg: str, cs: list[str], holders: list[str] | None = None) -> None:
            nonlocal tick
            steps.append(
                self._step(
                    tick,
                    procs,
                    action,
                    msg,
                    critical_section=cs,
                    waiting_queue=list(queue),
                    resources={"semaphore": sem, "holders": list(holders or [])},
                    shared_vars={"counter": counter},
                )
            )
            tick += 1

        emit("init", f"{name}: sem={sem} (initial slots={initial})", [])
        pids = sorted(procs.keys())

        for iteration in range(iterations):
            holders: list[str] = []
            emit("round_start", f"Iteration {iteration + 1}: processes contend for {name}", [], holders)

            for pid in pids:
                procs[pid] = "RUNNING"
                emit("P_wait", f"{pid}: P() - sem={sem}", [], holders)

                if sem == 0:
                    procs[pid] = "BLOCKED"
                    queue.append(pid)
                    emit("block", f"{pid} blocked - semaphore=0, joins wait queue", [], holders)
                    continue

                sem -= 1
                holders.append(pid)
                procs[pid] = "READY"
                emit("acquire", f"{pid} acquired resource - sem->{sem}", [], holders)

            while holders:
                pid = holders.pop(0)
                procs[pid] = "RUNNING"
                emit("enter_cs", f"{pid} enters critical section/resource use", [pid], holders + [pid])
                counter += 1
                emit("critical_section", f"{pid} in CS/resource use - counter={counter}", [pid], holders + [pid])

                if queue:
                    next_p = queue.pop(0)
                    procs[pid] = "READY"
                    procs[next_p] = "READY"
                    emit(
                        "V_signal",
                        f"{pid}: V() - transfers released slot to {next_p}; sem stays {sem}",
                        [],
                        holders,
                    )
                    holders.append(next_p)
                    emit("wakeup", f"{next_p} wakes because {pid} executed V()", [], holders)
                else:
                    sem += 1
                    procs[pid] = "READY"
                    emit("V_signal", f"{pid}: V() - sem->{sem} (no waiters)", [], holders)

                emit("exit_cs", f"{pid} left critical section", [], holders)

        for pid in procs:
            procs[pid] = "TERMINATED"
        emit("done", f"Semaphore done. counter={counter}", [])
        return steps, {"final_counter": counter, "initial_slots": initial, "mutual_exclusion": initial == 1}

    def _producer_consumer(self, config: dict) -> tuple[list, dict]:
        """
        Producer-Consumer problem with bounded buffer.

        Uses three semaphores:
        - mutex (binary): protects buffer access (initial=1)
        - empty: counts empty slots (initial=buffer_size)
        - full: counts filled slots (initial=0)

        Producer: P(empty), P(mutex), put item, V(mutex), V(full)
        Consumer: P(full), P(mutex), get item, V(mutex), V(empty)
        """
        buffer_size = int(config.get("buffer_size", 5))
        items = int(config.get("items", 6))
        steps: list[dict] = []
        tick = 0
        buffer: list[int] = []
        procs = {"Producer": "READY", "Consumer": "READY"}
        mutex = 1  # Binary semaphore for buffer protection
        empty_slots = buffer_size
        full_slots = 0
        produced = consumed = 0

        def emit(action: str, msg: str, active: str | None = None) -> None:
            nonlocal tick
            cs = [active] if active else []
            steps.append(
                self._step(
                    tick, procs, action, msg,
                    critical_section=cs,
                    resources={"mutex": mutex, "empty": empty_slots, "full": full_slots},
                    shared_vars={"buffer": buffer[:], "produced": produced, "consumed": consumed},
                )
            )
            tick += 1

        emit("init", f"Producer-Consumer: buffer_size={buffer_size}, items={items}. mutex=1, empty={buffer_size}, full=0", None)

        item_id = 0
        while consumed < items:
            # --- Producer ---
            if produced < items and empty_slots > 0:
                procs["Producer"] = "RUNNING"
                procs["Consumer"] = "READY"

                # P(empty) — wait for empty slot
                emit("P_empty", f"Producer: P(empty) — empty_slots={empty_slots}→{empty_slots-1}", "Producer")
                empty_slots -= 1

                # P(mutex) — enter critical section
                if mutex == 0:
                    emit("P_mutex_wait", "Producer: P(mutex) — waiting (mutex=0)", None)
                mutex = 0  # Acquire mutex
                emit("P_mutex", f"Producer: P(mutex) — acquired lock, mutex=0 (locked)", "Producer")

                # Produce item and add to buffer
                item_id += 1
                buffer.append(item_id)
                produced += 1
                emit("produce", f"Producer: added item {item_id} to buffer={buffer}", "Producer")

                # V(mutex) — release mutex
                mutex = 1
                emit("V_mutex", f"Producer: V(mutex) — released lock, mutex=1 (unlocked)", "Producer")

                # V(full) — signal item available
                full_slots += 1
                emit("V_full", f"Producer: V(full) — full_slots={full_slots}", None)
                procs["Producer"] = "READY"

            # --- Consumer ---
            if full_slots > 0 and consumed < produced:
                procs["Consumer"] = "RUNNING"
                procs["Producer"] = "READY"

                # P(full) — wait for item
                emit("P_full", f"Consumer: P(full) — full_slots={full_slots}→{full_slots-1}", "Consumer")
                full_slots -= 1

                # P(mutex) — enter critical section
                if mutex == 0:
                    emit("P_mutex_wait", "Consumer: P(mutex) — waiting (mutex=0)", None)
                mutex = 0  # Acquire mutex
                emit("P_mutex", f"Consumer: P(mutex) — acquired lock, mutex=0 (locked)", "Consumer")

                # Consume item from buffer
                item = buffer.pop(0)
                consumed += 1
                emit("consume", f"Consumer: removed item {item} from buffer={buffer}", "Consumer")

                # V(mutex) — release mutex
                mutex = 1
                emit("V_mutex", f"Consumer: V(mutex) — released lock, mutex=1 (unlocked)", "Consumer")

                # V(empty) — signal slot available
                empty_slots += 1
                emit("V_empty", f"Consumer: V(empty) — empty_slots={empty_slots}", None)
                procs["Consumer"] = "READY"

        procs = {k: "TERMINATED" for k in procs}
        emit("done", f"Producer-Consumer complete. Produced={produced}, Consumed={consumed}", None)
        return steps, {
            "produced": produced,
            "consumed": consumed,
            "buffer_size": buffer_size,
            "mutual_exclusion": True,
        }

    def _readers_writers(self, config: dict) -> tuple[list, dict]:
        """
        First Readers-Writers problem (readers-preference).

        read_count tracks active readers.
        First reader acquires write_lock; last reader releases it.
        Writers need exclusive access — blocked if any reader or writer active.

        Delegates to the contention model, which lets a group of readers share
        the critical section concurrently while writers wait.
        """
        return self._readers_writers_contention(config)

    def _readers_writers_contention(self, config: dict) -> tuple[list, dict]:
        """Readers-preference model: shared readers, exclusive writers."""
        readers = int(config.get("readers", 2))
        writers = int(config.get("writers", 2))
        ops = int(config.get("operations", 2))
        steps: list[dict] = []
        tick = 0
        read_count = 0
        write_lock = False
        procs: dict[str, str] = {}
        for i in range(readers):
            procs[f"R{i}"] = "READY"
        for i in range(writers):
            procs[f"W{i}"] = "READY"
        waiting: list[str] = []

        def emit(action: str, msg: str, cs: list[str]) -> None:
            nonlocal tick
            steps.append(
                self._step(
                    tick,
                    procs,
                    action,
                    msg,
                    critical_section=cs,
                    waiting_queue=list(waiting),
                    shared_vars={"read_count": read_count, "write_lock": write_lock},
                )
            )
            tick += 1

        emit("init", "Readers-Writers: readers share access; writers require exclusive access", [])

        for operation in range(ops):
            active_readers: list[str] = []
            emit("round_start", f"Operation {operation + 1}: reader group arrives before writers", [])

            for i in range(readers):
                pid = f"R{i}"
                procs[pid] = "RUNNING"
                emit("read_request", f"{pid} wants to read", active_readers)
                if read_count == 0:
                    write_lock = True
                    emit("read_lock", f"{pid} is first reader - acquires write_lock against writers", active_readers)
                read_count += 1
                active_readers.append(pid)
                procs[pid] = "RUNNING"
                emit("reading", f"{pid} starts reading with {read_count} active reader(s)", active_readers)

            for i in range(writers):
                pid = f"W{i}"
                procs[pid] = "BLOCKED"
                waiting.append(pid)
                emit("write_block", f"{pid} blocked - readers active, write_lock=True", active_readers)

            while active_readers:
                pid = active_readers.pop(0)
                read_count -= 1
                procs[pid] = "READY"
                if read_count == 0:
                    write_lock = False
                    emit("read_release", f"{pid} is last reader - releases write_lock", active_readers)
                else:
                    emit("read_done", f"{pid} finishes; {read_count} reader(s) still active", active_readers)

            while waiting:
                pid = waiting.pop(0)
                procs[pid] = "RUNNING"
                write_lock = True
                emit("writing", f"{pid} writes exclusively - no readers active", [pid])
                write_lock = False
                procs[pid] = "READY"
                emit("write_release", f"{pid} releases write_lock", [])

        for pid in procs:
            procs[pid] = "TERMINATED"
        emit("done", "Readers-Writers complete", [])
        return steps, {"readers": readers, "writers": writers, "reader_sharing": True}

    def _monitor(self, config: dict) -> tuple[list, dict]:
        """
        Monitor with condition variable (signal-and-continue semantics).

        P0 enters first, increments data, then signals waiting processes.
        P1..Pn enter, find data==0, call wait() — releasing the monitor lock.
        P0 signals each waiter in turn; each wakes, re-checks condition, proceeds.
        """
        n = int(config.get("processes", 3))
        steps: list[dict] = []
        tick = 0
        monitor_lock = False
        condition_queue: list[str] = []
        shared_data = 0
        procs = {f"P{i}": "READY" for i in range(n)}

        def emit(action: str, msg: str, cs: list[str]) -> None:
            nonlocal tick
            steps.append(
                self._step(
                    tick, procs, action, msg,
                    critical_section=cs, waiting_queue=list(condition_queue),
                    resources={"monitor_locked": monitor_lock},
                    shared_vars={"data": shared_data},
                )
            )
            tick += 1

        emit("init", "Monitor initialized — condition variable cv, shared data=0", [])

        # Phase 1: P1..Pn-1 enter, find data==0, call wait()
        for i in range(1, n):
            pid = f"P{i}"
            procs[pid] = "RUNNING"
            monitor_lock = True
            emit("enter_monitor", f"{pid} enters monitor — acquires monitor lock", [pid])
            emit("monitor_cs", f"{pid} checks condition: data={shared_data} (need data>0)", [pid])
            # Condition not met — call wait()
            procs[pid] = "WAITING"
            condition_queue.append(pid)
            monitor_lock = False
            emit("wait_cv", f"{pid}: wait(cv) — releases monitor lock, joins condition queue", [])

        # Phase 2: P0 enters, updates data, signals all waiters
        pid0 = "P0"
        procs[pid0] = "RUNNING"
        monitor_lock = True
        emit("enter_monitor", f"{pid0} enters monitor — acquires monitor lock", [pid0])
        shared_data += 1
        emit("update", f"{pid0} updates data={shared_data}", [pid0])

        # Broadcast to all waiting processes (signal_all / notifyAll).
        # Each individual signal(cv) wakes exactly ONE waiter; calling it in a
        # loop until the queue is empty is equivalent to broadcast(cv) /
        # notifyAll() in Java. Labelled correctly here to distinguish from a
        # single signal() call.
        while condition_queue:
            wake = condition_queue.pop(0)
            emit("signal_all", f"{pid0}: broadcast(cv) / signal_all — waking {wake} ({len(condition_queue)} still queued)", [pid0])
            procs[wake] = "WAITING"
            # Woken process re-enters monitor after P0 exits (signal-and-continue)
            emit("wakeup", f"{wake} woken — will compete for monitor lock after {pid0} exits (signal-and-continue)", [pid0])

        monitor_lock = False
        procs[pid0] = "READY"
        emit("exit_monitor", f"{pid0} exits monitor — releases monitor lock", [])

        # Phase 3: woken processes re-enter, check condition, proceed
        for i in range(1, n):
            pid = f"P{i}"
            procs[pid] = "RUNNING"
            monitor_lock = True
            emit("enter_monitor", f"{pid} re-enters monitor after being signalled", [pid])
            emit("monitor_cs", f"{pid} re-checks condition: data={shared_data} ✓", [pid])
            shared_data += 1
            emit("update", f"{pid} updates data={shared_data}", [pid])
            monitor_lock = False
            procs[pid] = "READY"
            emit("exit_monitor", f"{pid} exits monitor", [])

        for pid in procs:
            procs[pid] = "TERMINATED"
        emit("done", f"Monitor complete. data={shared_data}", [])
        return steps, {"final_data": shared_data}

    def _race_condition(self, config: dict) -> tuple[list, dict]:
        """
        Race condition demonstration — shows the lost-update problem.

        UNSAFE mode: Multiple processes read-modify-write without synchronization.
        The classic interleaving: P0 reads X, P1 reads X, both compute X+1, both write X+1.
        Result: two increments but counter only increases by 1 (lost update).

        SAFE mode: Mutex ensures only one process can be in the critical section.
        """
        unsafe = config.get("corrected", False) is False
        n = int(config.get("processes", 2))  # Use 2 processes for clear demo
        increments = int(config.get("increments", 3))
        steps: list[dict] = []
        tick = 0
        counter = 0
        procs = {f"P{i}": "READY" for i in range(n)}
        lock = False
        wait_queue: list[str] = []

        def emit(action: str, msg: str, cs: list[str]) -> None:
            nonlocal tick
            steps.append(
                self._step(
                    tick, procs, action, msg,
                    critical_section=cs,
                    waiting_queue=list(wait_queue),
                    shared_vars={"counter": counter, "unsafe_mode": unsafe},
                    resources={"lock": lock},
                )
            )
            tick += 1

        mode = "UNSAFE (no synchronization)" if unsafe else "SAFE (mutex protected)"
        emit("init", f"Race condition demo — {mode}. {n} processes, {increments} increments each.", [])

        expected = n * increments

        for round_num in range(increments):
            emit("round_start", f"--- Round {round_num + 1} of {increments} ---", [])

            # In unsafe mode: simulate the classic interleaved lost-update scenario
            if unsafe and n >= 2:
                # Both processes read the current value simultaneously
                for i in range(n):
                    pid = f"P{i}"
                    procs[pid] = "RUNNING"
                emit("read_phase", f"All processes read counter={counter} simultaneously", [])

                # Store what each process "saw" locally
                local_values = {f"P{i}": counter for i in range(n)}

                # Each process computes its new value
                for i in range(n):
                    pid = f"P{i}"
                    emit("compute", f"{pid}: local_copy={local_values[pid]}, computes local+1={local_values[pid]+1}", [])

                # Now the writes happen — last write wins, causing lost updates
                for i in range(n):
                    pid = f"P{i}"
                    # Each writes what they computed, overwriting others
                    counter = local_values[pid] + 1
                    emit("write", f"{pid} writes counter={counter} (overwrites previous!)", [])
                    procs[pid] = "READY"

                # Demonstrate the lost update: all N processes incremented, but counter only went up by 1
                emit("lost_update", f"LOST UPDATE: {n} processes tried to increment, counter only increased by 1", [])

            else:
                # SAFE mode: mutex protects the critical section
                for i in range(n):
                    pid = f"P{i}"
                    procs[pid] = "RUNNING"
                    emit("request_lock", f"{pid} requests mutex", [])

                    if lock:
                        # Another process holds the lock — must wait
                        procs[pid] = "BLOCKED"
                        wait_queue.append(pid)
                        emit("blocked", f"{pid} blocked — mutex held by another process", [])
                        # In sequential sim, the holder will release before we proceed
                        wait_queue.remove(pid)
                        procs[pid] = "RUNNING"
                        emit("unblocked", f"{pid} acquired mutex after waiting", [])

                    lock = True
                    emit("enter_cs", f"{pid} enters critical section — lock=True", [pid])

                    # Read-modify-write inside CS
                    old_val = counter
                    emit("read", f"{pid} reads counter={old_val}", [pid])
                    counter = old_val + 1
                    emit("write", f"{pid} writes counter={counter}", [pid])

                    # Release lock
                    lock = False
                    procs[pid] = "READY"
                    emit("exit_cs", f"{pid} exits critical section — lock=False", [])

        # Calculate what we expect vs what we got
        if unsafe and n >= 2:
            # In unsafe mode with interleaving, we lose (n-1) increments per round
            # So final counter = increments (each round only adds 1 instead of n)
            final_counter = increments
            race_detected = True
        else:
            final_counter = expected
            race_detected = False

        # Update counter to reflect the actual outcome
        counter = final_counter

        for pid in procs:
            procs[pid] = "TERMINATED"
        emit(
            "done",
            f"Final counter={counter}, expected={expected} ({n} processes × {increments} increments). "
            f"{'⚠ RACE CONDITION DETECTED — lost updates occurred!' if race_detected else '✓ Correct — mutual exclusion prevented race'}",
            [],
        )
        return steps, {
            "final_counter": counter,
            "expected": expected,
            "race_detected": race_detected,
            "corrected": not unsafe,
            "lost_updates": expected - counter if race_detected else 0,
        }

    def _deadlock_demo(self, config: dict) -> tuple[list, dict]:
        steps: list[dict] = []
        tick = 0
        resources = {"R1": "P0", "R2": None}
        procs = {"P0": "RUNNING", "P1": "RUNNING"}

        def emit(action: str, msg: str, deadlock: bool = False) -> None:
            nonlocal tick
            steps.append(
                self._step(
                    tick, procs, action, msg,
                    critical_section=[],
                    waiting_queue=["P1"] if deadlock else [],
                    resources={"R1": resources["R1"], "R2": resources["R2"]},
                    shared_vars={"deadlock": deadlock},
                )
            )
            tick += 1

        emit("init", "P0 holds R1, wants R2; P1 holds R2, wants R1", False)
        resources = {"R1": "P0", "R2": "P1"}
        emit("hold_wait", "P0 holds R1, requests R2", False)
        emit("hold_wait", "P1 holds R2, requests R1", False)
        procs["P0"] = "BLOCKED"
        procs["P1"] = "BLOCKED"
        emit("deadlock", "DEADLOCK: circular wait — P0↔P1", True)
        emit("starvation", "Processes cannot proceed without external intervention", True)
        procs = {k: "BLOCKED" for k in procs}
        emit("done", "Deadlock demonstration complete", True)
        return steps, {"deadlock": True, "recovery": "Break circular wait or preempt resources"}
