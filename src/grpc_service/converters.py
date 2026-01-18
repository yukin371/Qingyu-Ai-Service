"""
数据转换工具 - Protobuf消息与Python字典之间的转换
"""
from typing import Dict, List, Any, Optional


def outline_dict_to_proto_data(outline_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    将大纲Python字典转换为protobuf消息数据

    Args:
        outline_dict: Python字典格式的大纲数据

    Returns:
        可用于protobuf消息的字典
    """
    chapters_data = []
    for chapter in outline_dict.get("chapters", []):
        chapter_data = {
            "chapter_id": chapter.get("chapter_id", 0),
            "title": chapter.get("title", ""),
            "summary": chapter.get("summary", ""),
            "key_events": chapter.get("key_events", []),
            "characters_involved": chapter.get("characters_involved", []),
            "conflict_type": chapter.get("conflict_type", ""),
            "emotional_tone": chapter.get("emotional_tone", ""),
            "estimated_word_count": chapter.get("estimated_word_count", 0),
            "chapter_goal": chapter.get("chapter_goal", ""),
            "cliffhanger": chapter.get("cliffhanger", ""),
        }
        chapters_data.append(chapter_data)

    story_arc = outline_dict.get("story_arc", {})
    story_arc_data = {
        "setup": story_arc.get("setup", []),
        "rising_action": story_arc.get("rising_action", []),
        "climax": story_arc.get("climax", []),
        "falling_action": story_arc.get("falling_action", []),
        "resolution": story_arc.get("resolution", []),
    }

    return {
        "title": outline_dict.get("title", ""),
        "genre": outline_dict.get("genre", ""),
        "core_theme": outline_dict.get("core_theme", ""),
        "target_audience": outline_dict.get("target_audience", ""),
        "estimated_total_words": outline_dict.get("estimated_total_words", 0),
        "chapters": chapters_data,
        "story_arc": story_arc_data,
    }


def characters_dict_to_proto_data(characters_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    将角色Python字典转换为protobuf消息数据

    Args:
        characters_dict: Python字典格式的角色数据

    Returns:
        可用于protobuf消息的字典
    """
    characters_data = []
    for char in characters_dict.get("characters", []):
        personality = char.get("personality", {})
        personality_data = {
            "traits": personality.get("traits", []),
            "strengths": personality.get("strengths", []),
            "weaknesses": personality.get("weaknesses", []),
            "core_values": personality.get("core_values", ""),
            "fears": personality.get("fears", ""),
        }

        background = char.get("background", {})
        background_data = {
            "summary": background.get("summary", ""),
            "family": background.get("family", ""),
            "education": background.get("education", ""),
            "key_experiences": background.get("key_experiences", []),
        }

        relationships_data = []
        for rel in char.get("relationships", []):
            rel_data = {
                "character": rel.get("character", ""),
                "relation_type": rel.get("relation_type", ""),
                "description": rel.get("description", ""),
                "dynamics": rel.get("dynamics", ""),
            }
            relationships_data.append(rel_data)

        dev_arc = char.get("development_arc", {})
        dev_arc_data = {
            "starting_point": dev_arc.get("starting_point", ""),
            "turning_points": dev_arc.get("turning_points", []),
            "ending_point": dev_arc.get("ending_point", ""),
            "growth_theme": dev_arc.get("growth_theme", ""),
        }

        char_data = {
            "character_id": char.get("character_id", ""),
            "name": char.get("name", ""),
            "role_type": char.get("role_type", ""),
            "importance": char.get("importance", ""),
            "age": char.get("age", 0),
            "gender": char.get("gender", ""),
            "appearance": char.get("appearance", ""),
            "personality": personality_data,
            "background": background_data,
            "motivation": char.get("motivation", ""),
            "relationships": relationships_data,
            "development_arc": dev_arc_data,
            "role_in_story": char.get("role_in_story", ""),
            "first_appearance": char.get("first_appearance", 0),
            "chapters_involved": char.get("chapters_involved", []),
        }
        characters_data.append(char_data)

    network = characters_dict.get("relationship_network", {})

    alliances = []
    for alliance in network.get("alliances", []):
        alliances.append({"members": alliance})

    conflicts = []
    for conflict in network.get("conflicts", []):
        conflicts.append({"parties": conflict})

    mentorships = []
    for mentorship in network.get("mentorships", []):
        mentorships.append({
            "mentor": mentorship.get("mentor", ""),
            "student": mentorship.get("student", ""),
        })

    network_data = {
        "alliances": alliances,
        "conflicts": conflicts,
        "mentorships": mentorships,
    }

    return {
        "characters": characters_data,
        "relationship_network": network_data,
    }


def plot_dict_to_proto_data(plot_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    将情节Python字典转换为protobuf消息数据

    Args:
        plot_dict: Python字典格式的情节数据

    Returns:
        可用于protobuf消息的字典
    """
    events_data = []
    for event in plot_dict.get("timeline_events", []):
        impact = event.get("impact", {})
        impact_data = {
            "on_plot": impact.get("on_plot", ""),
            "on_characters": impact.get("on_characters", {}),
            "emotional_impact": impact.get("emotional_impact", ""),
        }

        event_data = {
            "event_id": event.get("event_id", ""),
            "timestamp": event.get("timestamp", ""),
            "location": event.get("location", ""),
            "title": event.get("title", ""),
            "description": event.get("description", ""),
            "participants": event.get("participants", []),
            "event_type": event.get("event_type", ""),
            "impact": impact_data,
            "causes": event.get("causes", []),
            "consequences": event.get("consequences", []),
            "chapter_id": event.get("chapter_id", 0),
        }
        events_data.append(event_data)

    threads_data = []
    for thread in plot_dict.get("plot_threads", []):
        thread_data = {
            "thread_id": thread.get("thread_id", ""),
            "title": thread.get("title", ""),
            "description": thread.get("description", ""),
            "type": thread.get("type", ""),
            "events": thread.get("events", []),
            "starting_event": thread.get("starting_event", ""),
            "climax_event": thread.get("climax_event", ""),
            "resolution_event": thread.get("resolution_event", ""),
            "characters_involved": thread.get("characters_involved", []),
        }
        threads_data.append(thread_data)

    conflicts_data = []
    for conflict in plot_dict.get("conflicts", []):
        conflict_data = {
            "conflict_id": conflict.get("conflict_id", ""),
            "type": conflict.get("type", ""),
            "parties": conflict.get("parties", []),
            "description": conflict.get("description", ""),
            "escalation_events": conflict.get("escalation_events", []),
            "resolution_event": conflict.get("resolution_event", ""),
        }
        conflicts_data.append(conflict_data)

    key_points = plot_dict.get("key_plot_points", {})
    key_points_data = {
        "inciting_incident": key_points.get("inciting_incident", ""),
        "plot_point_1": key_points.get("plot_point_1", ""),
        "midpoint": key_points.get("midpoint", ""),
        "plot_point_2": key_points.get("plot_point_2", ""),
        "climax": key_points.get("climax", ""),
        "resolution": key_points.get("resolution", ""),
    }

    return {
        "timeline_events": events_data,
        "plot_threads": threads_data,
        "conflicts": conflicts_data,
        "key_plot_points": key_points_data,
    }


def diagnostic_report_dict_to_proto_data(report_dict: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    将诊断报告Python字典转换为protobuf消息数据

    Args:
        report_dict: Python字典格式的诊断报告数据

    Returns:
        可用于protobuf消息的字典
    """
    if not report_dict:
        return None

    issues_data = []
    for issue in report_dict.get("issues", []):
        issue_data = {
            "id": issue.get("id", ""),
            "severity": issue.get("severity", ""),
            "category": issue.get("category", ""),
            "sub_category": issue.get("sub_category", ""),
            "title": issue.get("title", ""),
            "description": issue.get("description", ""),
            "root_cause": issue.get("root_cause", ""),
            "affected_entities": issue.get("affected_entities", []),
            "impact": issue.get("impact", ""),
        }
        issues_data.append(issue_data)

    return {
        "passed": report_dict.get("passed", False),
        "quality_score": report_dict.get("quality_score", 0),
        "issues": issues_data,
        "correction_strategy": report_dict.get("correction_strategy", ""),
        "affected_agents": report_dict.get("affected_agents", []),
        "reasoning_chain": report_dict.get("reasoning_chain", []),
    }

