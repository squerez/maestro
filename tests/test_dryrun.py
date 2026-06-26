from maestro.pipeline.dryrun import DryRunResult, StepDryRunResult


def _step(name="s", plugin="p", records_in=10, records_out=10, skipped=False, runtime="polars"):
    return StepDryRunResult(
        name=name,
        plugin=plugin,
        records_in=records_in,
        records_out=records_out,
        duration_seconds=0.5,
        runtime_type=runtime,
        skipped=skipped,
    )


def test_total_records_out_sums_non_skipped():
    result = DryRunResult(
        pipeline="p",
        total_duration_seconds=1.0,
        step_results=[
            _step("a", records_out=50),
            _step("b", records_out=30),
            _step("c", records_out=10, skipped=True),
        ],
    )
    assert result.total_records_out == 80


def test_total_records_out_all_skipped():
    result = DryRunResult(
        pipeline="p",
        total_duration_seconds=1.0,
        step_results=[_step(skipped=True), _step(skipped=True)],
    )
    assert result.total_records_out == 0


def test_total_records_out_empty():
    result = DryRunResult(pipeline="p", total_duration_seconds=0.0)
    assert result.total_records_out == 0


def test_summary_contains_pipeline_name():
    result = DryRunResult(pipeline="my_pipeline", total_duration_seconds=2.5)
    assert "my_pipeline" in result.summary()


def test_summary_contains_duration():
    result = DryRunResult(pipeline="p", total_duration_seconds=3.14)
    assert "3.14" in result.summary()


def test_summary_shows_ok_for_non_skipped():
    result = DryRunResult(
        pipeline="p",
        total_duration_seconds=1.0,
        step_results=[_step("ingest", skipped=False)],
    )
    summary = result.summary()
    assert " OK " in summary
    assert "ingest" in summary


def test_summary_shows_skip_for_skipped():
    result = DryRunResult(
        pipeline="p",
        total_duration_seconds=1.0,
        step_results=[_step("write", skipped=True)],
    )
    assert "SKIP" in result.summary()


def test_summary_shows_runtime_type():
    result = DryRunResult(
        pipeline="p",
        total_duration_seconds=1.0,
        step_results=[_step(runtime="databricks")],
    )
    assert "databricks" in result.summary()


def test_summary_step_count():
    result = DryRunResult(
        pipeline="p",
        total_duration_seconds=1.0,
        step_results=[_step("a"), _step("b"), _step("c")],
    )
    assert "3" in result.summary()
