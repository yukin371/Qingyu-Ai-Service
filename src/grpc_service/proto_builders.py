"""
Protobuf消息构建器 - 将Python字典转换为protobuf消息对象
"""
from typing import Dict, List, Any
from src.grpc_service import ai_service_pb2


def build_outline_proto(outline_dict: Dict[str, Any]) -> ai_service_pb2.OutlineData:
    """
    从字典构建OutlineData protobuf消息

    Args:
        outline_dict: 大纲字典数据

    Returns:
        OutlineData protobuf消息
    """
    chapters = []
    for chapter in outline_dict.get("chapters", []):
        chapter_proto = ai_service_pb2.ChapterData(
            chapter_id=chapter.get("chapter_id", 0),
            title=chapter.get("title", ""),
            summary=chapter.get("summary", ""),
            key_events=chapter.get("key_events", []),
            characters_involved=chapter.get("characters_involved", []),
            conflict_type=chapter.get("conflict_type", ""),
            emotional_tone=chapter.get("emotional_tone", ""),
            estimated_word_count=chapter.get("estimated_word_count", 0),
            chapter_goal=chapter.get("chapter_goal", ""),
            cliffhanger=chapter.get("cliffhanger", ""),
        )
        chapters.append(chapter_proto)

    story_arc_dict = outline_dict.get("story_arc", {})
    story_arc = ai_service_pb2.StoryArc(
        setup=story_arc_dict.get("setup", []),
        rising_action=story_arc_dict.get("rising_action", []),
        climax=story_arc_dict.get("climax", []),
        falling_action=story_arc_dict.get("falling_action", []),
        resolution=story_arc_dict.get("resolution", []),
    )

    return ai_service_pb2.OutlineData(
        title=outline_dict.get("title", ""),
        genre=outline_dict.get("genre", ""),
        core_theme=outline_dict.get("core_theme", ""),
        target_audience=outline_dict.get("target_audience", ""),
        estimated_total_words=outline_dict.get("estimated_total_words", 0),
        chapters=chapters,
        story_arc=story_arc,
    )


def build_characters_proto(characters_dict: Dict[str, Any]) -> ai_service_pb2.CharactersData:
    """
    从字典构建CharactersData protobuf消息

    Args:
        characters_dict: 角色字典数据

    Returns:
        CharactersData protobuf消息
    """
    characters = []
    for char in characters_dict.get("characters", []):
        personality_dict = char.get("personality", {})
        personality = ai_service_pb2.PersonalityData(
            traits=personality_dict.get("traits", []),
            strengths=personality_dict.get("strengths", []),
            weaknesses=personality_dict.get("weaknesses", []),
            core_values=personality_dict.get("core_values", ""),
            fears=personality_dict.get("fears", ""),
        )

        background_dict = char.get("background", {})
        background = ai_service_pb2.BackgroundData(
            summary=background_dict.get("summary", ""),
            family=background_dict.get("family", ""),
            education=background_dict.get("education", ""),
            key_experiences=background_dict.get("key_experiences", []),
        )

        relationships = []
        for rel in char.get("relationships", []):
            rel_proto = ai_service_pb2.RelationshipData(
                character=rel.get("character", ""),
                relation_type=rel.get("relation_type", ""),
                description=rel.get("description", ""),
                dynamics=rel.get("dynamics", ""),
            )
            relationships.append(rel_proto)

        dev_arc_dict = char.get("development_arc", {})
        dev_arc = ai_service_pb2.DevelopmentArc(
            starting_point=dev_arc_dict.get("starting_point", ""),
            turning_points=dev_arc_dict.get("turning_points", []),
            ending_point=dev_arc_dict.get("ending_point", ""),
            growth_theme=dev_arc_dict.get("growth_theme", ""),
        )

        char_proto = ai_service_pb2.CharacterData(
            character_id=char.get("character_id", ""),
            name=char.get("name", ""),
            role_type=char.get("role_type", ""),
            importance=char.get("importance", ""),
            age=char.get("age", 0),
            gender=char.get("gender", ""),
            appearance=char.get("appearance", ""),
            personality=personality,
            background=background,
            motivation=char.get("motivation", ""),
            relationships=relationships,
            development_arc=dev_arc,
            role_in_story=char.get("role_in_story", ""),
            first_appearance=char.get("first_appearance", 0),
            chapters_involved=char.get("chapters_involved", []),
        )
        characters.append(char_proto)

    network_dict = characters_dict.get("relationship_network", {})

    alliances = []
    for alliance in network_dict.get("alliances", []):
        alliances.append(ai_service_pb2.Alliance(members=alliance))

    conflicts = []
    for conflict in network_dict.get("conflicts", []):
        conflicts.append(ai_service_pb2.Conflict(parties=conflict))

    mentorships = []
    for mentorship in network_dict.get("mentorships", []):
        mentorships.append(ai_service_pb2.Mentorship(
            mentor=mentorship.get("mentor", ""),
            student=mentorship.get("student", ""),
        ))

    network = ai_service_pb2.RelationshipNetwork(
        alliances=alliances,
        conflicts=conflicts,
        mentorships=mentorships,
    )

    return ai_service_pb2.CharactersData(
        characters=characters,
        relationship_network=network,
    )


def build_plot_proto(plot_dict: Dict[str, Any]) -> ai_service_pb2.PlotData:
    """
    从字典构建PlotData protobuf消息

    Args:
        plot_dict: 情节字典数据

    Returns:
        PlotData protobuf消息
    """
    events = []
    for event in plot_dict.get("timeline_events", []):
        impact_dict = event.get("impact", {})
        impact = ai_service_pb2.EventImpact(
            on_plot=impact_dict.get("on_plot", ""),
            on_characters=impact_dict.get("on_characters", {}),
            emotional_impact=impact_dict.get("emotional_impact", ""),
        )

        event_proto = ai_service_pb2.TimelineEventData(
            event_id=event.get("event_id", ""),
            timestamp=event.get("timestamp", ""),
            location=event.get("location", ""),
            title=event.get("title", ""),
            description=event.get("description", ""),
            participants=event.get("participants", []),
            event_type=event.get("event_type", ""),
            impact=impact,
            causes=event.get("causes", []),
            consequences=event.get("consequences", []),
            chapter_id=event.get("chapter_id", 0),
        )
        events.append(event_proto)

    threads = []
    for thread in plot_dict.get("plot_threads", []):
        thread_proto = ai_service_pb2.PlotThread(
            thread_id=thread.get("thread_id", ""),
            title=thread.get("title", ""),
            description=thread.get("description", ""),
            type=thread.get("type", ""),
            events=thread.get("events", []),
            starting_event=thread.get("starting_event", ""),
            climax_event=thread.get("climax_event", ""),
            resolution_event=thread.get("resolution_event", ""),
            characters_involved=thread.get("characters_involved", []),
        )
        threads.append(thread_proto)

    conflicts = []
    for conflict in plot_dict.get("conflicts", []):
        conflict_proto = ai_service_pb2.ConflictData(
            conflict_id=conflict.get("conflict_id", ""),
            type=conflict.get("type", ""),
            parties=conflict.get("parties", []),
            description=conflict.get("description", ""),
            escalation_events=conflict.get("escalation_events", []),
            resolution_event=conflict.get("resolution_event", ""),
        )
        conflicts.append(conflict_proto)

    key_points_dict = plot_dict.get("key_plot_points", {})
    key_points = ai_service_pb2.KeyPlotPoints(
        inciting_incident=key_points_dict.get("inciting_incident", ""),
        plot_point_1=key_points_dict.get("plot_point_1", ""),
        midpoint=key_points_dict.get("midpoint", ""),
        plot_point_2=key_points_dict.get("plot_point_2", ""),
        climax=key_points_dict.get("climax", ""),
        resolution=key_points_dict.get("resolution", ""),
    )

    return ai_service_pb2.PlotData(
        timeline_events=events,
        plot_threads=threads,
        conflicts=conflicts,
        key_plot_points=key_points,
    )

