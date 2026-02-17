from homebrew_cdn_m1_server.domain.workflows.reconcile_catalog import build_delta


def test_build_delta_given_previous_and_current_then_classifies_changes():
    previous = {
        "/a.pkg": (10, 1),
        "/b.pkg": (20, 2),
    }
    current = {
        "/b.pkg": (20, 99),
        "/c.pkg": (30, 3),
    }

    delta = build_delta(previous, current)

    assert delta.added == ("/c.pkg",)
    assert delta.updated == ("/b.pkg",)
    assert delta.removed == ("/a.pkg",)
    assert delta.has_changes is True
