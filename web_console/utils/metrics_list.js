const metrics_list = {
    data_join: [
        {
            query: "name%20:%22data_block_dump_duration%22",
            mode: "avg",
            title: "data_block_dump_duration"
        },
        {
            query: "name%20:%22data_block_index%22",
            mode: "avg",
            title: "data_block_index"
        },
        {
            query: "name%20:%22stats_cum_join_num%22",
            mode: "avg",
            title: "stats_cum_join_num"
        },
        {
            query: "name%20:%22actual_cum_join_num%22",
            mode: "avg",
            title: "actual_cum_join_num"
        },
        {
            query: "name%20:%22leader_stats_index%22",
            mode: "avg",
            title: "leader_stats_index"
        },
        {
            query: "name%20:%22follower_stats_index%22",
            mode: "avg",
            title: "follower_stats_index"
        },
        {
            query: "name%20:%22example_id_dump_duration%22",
            mode: "avg",
            title: "example_id_dump_duration"
        },
        {
            query: "name%20:%22example_dump_file_index%22",
            mode: "avg",
            title: "example_dump_file_index"
        },
        {
            query: "name%20:%22example_id_dumped_index%22",
            mode: "avg",
            title: "example_id_dumped_index"
        },
        {
            query: "name%20:%22stats_cum_join_num%22",
            mode: "avg",
            title: "stats_cum_join_num"
        },
        {
            query: "name%20:%22actual_cum_join_num%22",
            mode: "avg",
            title: "actual_cum_join_num"
        },
        {
            query: "name%20:%22leader_stats_index%22",
            mode: "avg",
            title: "leader_stats_index"
        },
        {
            query: "name%20:%22follower_stats_index%22",
            mode: "avg",
            title: "follower_stats_index"
        },
        {
            query: "name%20:%22leader_join_rate_percent%22",
            mode: "avg",
            title: "leader_join_rate_percent"
        },
        {
            query: "name%20:%22follower_join_rate_percent%22",
            mode: "avg",
            title: "follower_join_rate_percent"
        }
    ],
    psi_data_join: [
        {
            query: "name%20:%22data_block_dump_duration%22",
            mode: "avg",
            title: "data_block_dump_duration"
        },
        {
            query: "name%20:%22data_block_index%22",
            mode: "avg",
            title: "data_block_index"
        },
        {
            query: "name%20:%22stats_cum_join_num%22",
            mode: "avg",
            title: "stats_cum_join_num"
        },
        {
            query: "name%20:%22actual_cum_join_num%22",
            mode: "avg",
            title: "actual_cum_join_num"
        },
        {
            query: "name%20:%22leader_stats_index%22",
            mode: "avg",
            title: "leader_stats_index"
        },
        {
            query: "name%20:%22follower_stats_index%22",
            mode: "avg",
            title: "follower_stats_index"
        },
        {
            query: "name%20:%22example_id_dump_duration%22",
            mode: "avg",
            title: "example_id_dump_duration"
        },
        {
            query: "name%20:%22example_dump_file_index%22",
            mode: "avg",
            title: "example_dump_file_index"
        },
        {
            query: "name%20:%22example_id_dumped_index%22",
            mode: "avg",
            title: "example_id_dumped_index"
        },
        {
            query: "name%20:%22stats_cum_join_num%22",
            mode: "avg",
            title: "stats_cum_join_num"
        },
        {
            query: "name%20:%22actual_cum_join_num%22",
            mode: "avg",
            title: "actual_cum_join_num"
        },
        {
            query: "name%20:%22leader_stats_index%22",
            mode: "avg",
            title: "leader_stats_index"
        },
        {
            query: "name%20:%22follower_stats_index%22",
            mode: "avg",
            title: "follower_stats_index"
        },
        {
            query: "name%20:%22leader_join_rate_percent%22",
            mode: "avg",
            title: "leader_join_rate_percent"
        },
        {
            query: "name%20:%22follower_join_rate_percent%22",
            mode: "avg",
            title: "follower_join_rate_percent"
        }
    ],
    tree_model: [

    ],
    nn_model: [
        {
            query: "name%20:%22auc%22",
            mode: "avg",
            title: "auc"
        },
        {
            query: "name%20:%22loss%22",
            mode: "avg",
            title: "loss"
        },
        {
            query: "name%20:%22receive_timer%22",
            mode: "avg",
            title: "receive spend"
        },
        {
            query: "name%20:%22iter_spend%22",
            mode: "avg",
            title: "per session run spend"
        },
        {
            query: "name%20:%22resend_counter%22",
            mode: "sum",
            title: "count of resend"
        },
        {
            query: "name%20:%22send_counter%22",
            mode: "sum",
            title: "count of send"
        },
        {
            query: "name%20:%22reconnect_counter%22",
            mode: "sum",
            title: "count of reconnect"
        },
        {
            query: "name%20:%22load_data_block_counter%22",
            mode: "sum",
            title: "count of load data block"
        },
        {
            query: "name%20:%22load_data_block_fail_counter%22",
            mode: "sum",
            title: "count of fail to load data block"
        }
    ]
};

module.exports = { metrics_list }