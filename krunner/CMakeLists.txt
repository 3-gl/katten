set(CMAKE_INSTALL_DEFAULT_COMPONENT_NAME krunner)

kcoreaddons_add_plugin(kattenrunner
    SOURCES kattenrunner.cpp
    INSTALL_NAMESPACE "kf6/krunner"
)
target_link_libraries(kattenrunner PRIVATE
    KF6::Runner
    KF6::I18n
    KF6::ConfigCore
    Qt6::DBus
    Qt6::Core
)
