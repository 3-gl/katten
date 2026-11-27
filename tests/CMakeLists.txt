find_package(Qt6 REQUIRED COMPONENTS Test)

ecm_add_test(TEST_NAME markdownrenderertest
    markdownrenderertest.cpp
    ${CMAKE_SOURCE_DIR}/src/MarkdownRenderer.cpp
    LINK_LIBRARIES Qt6::Test Qt6::Gui Qt6::Svg Qt6::Core)
target_include_directories(markdownrenderertest PRIVATE ${CMAKE_SOURCE_DIR}/src)

ecm_add_test(TEST_NAME conversationstoretest
    conversationstoretest.cpp
    ${CMAKE_SOURCE_DIR}/src/Conversation.cpp
    ${CMAKE_SOURCE_DIR}/src/ConversationStore.cpp
    LINK_LIBRARIES Qt6::Test Qt6::Core)
target_include_directories(conversationstoretest PRIVATE ${CMAKE_SOURCE_DIR}/src)
