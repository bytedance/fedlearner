import matplotlib
import matplotlib.pyplot as plt
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42
matplotlib.rcParams.update({'font.size': 21}) # change fonts size when text is too small to read
from pytz import timezone
import datetime
west_tz = timezone('US/Pacific')

def visualize_roc_auc(fpr, tpr, label):
    fig, axes = plt.subplots(1, 1, figsize=(12, 10))
    colors = ["#FFC222", '#33FF82', "#cc8374", '#33A8FF', "#c519cf", '#F67007', "#171ca6", '#335EFF', "#FF333C",
              "#66E2F1", "#EE669C", '#778EEE', "#5ec22d", "#e81e40"]
    # axes.plot(fpr, tpr, color=colors[0], linewidth=3.0, label=label)
    axes.plot(fpr, tpr, "o", color=colors[0], label=label)

    axes.set_xlabel('FPR', fontsize=20)
    axes.set_ylabel("TPR", fontsize=20)
    plt.grid(True, axis = "y", ls = "--")
    plt.legend(fontsize=12)
    stamp = datetime.datetime.now(tz=west_tz).strftime("%Y%m%d_%H_%M_%S")
    file_name = "figures/roc_auc/" + str(stamp) + "_" + str(label)
    plt.savefig(file_name + '.pdf')
    # plt.savefig(file_name + '.png')
    # plt.show()
