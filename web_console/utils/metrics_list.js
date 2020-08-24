const metrics_list = {
    data_join: [

    ],
    psi_data_join: [

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