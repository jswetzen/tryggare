import client


def test_first_claim_succeeds():
    assert client._claim_job("job-1") is True


def test_second_claim_of_inflight_job_fails():
    assert client._claim_job("job-1") is True
    assert client._claim_job("job-1") is False


def test_claim_after_successful_release_is_rejected():
    client._claim_job("job-1")
    client._release_job("job-1", completed=True)
    assert client._claim_job("job-1") is False


def test_claim_after_failed_release_is_allowed_again():
    client._claim_job("job-1")
    client._release_job("job-1", completed=False)
    assert client._claim_job("job-1") is True


def test_ring_buffer_evicts_oldest_completed_job():
    max_jobs = client._RECENT_JOBS_MAX
    for i in range(max_jobs):
        job_id = f"job-{i}"
        client._claim_job(job_id)
        client._release_job(job_id, completed=True)

    # Deque is now full (job-0..job-{max_jobs-1}). One more completion evicts
    # the oldest (job-0), making it claimable again; job-1 is still remembered.
    new_job = f"job-{max_jobs}"
    client._claim_job(new_job)
    client._release_job(new_job, completed=True)

    assert client._claim_job("job-0") is True
    assert client._claim_job("job-1") is False
