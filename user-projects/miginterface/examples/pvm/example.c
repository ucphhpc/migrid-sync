#include <stdio.h>
#include <stdlib.h>

#include <pvm3.h>

int main(int argc, char **argv) {
	int rank;
    int total;

    if(argc < 3) {
        fprintf(stderr, "err: missing argument\n");
        exit(-1);
    }

    total = atoi(argv[1]);

    // all tasks join the same group
	if((rank = pvm_joingroup("tasks")) < 0) {
		pvm_perror("Error joining group");
		exit(-1);
	}

    // the first task starts all the other
	if (rank == 0 && total > 1) {
        char *args[] = {argv[1], argv[2], NULL};
        int tids[total-1];

        printf("Starting %d tasks\n", total);

        // catch output from childs
        pvm_catchout(stderr);

        if (pvm_spawn("example", args, 0, NULL, total-1, tids) != total-1) {
            pvm_perror("Error spawning other tasks");
            exit(-1);
        }
	}

	printf("Rank=%d started with arg %s\n", rank, argv[2]);

    // after this all tasks have been started
    pvm_barrier("tasks", total);

    // here each task can do their work
    printf("Rank=%d working...\n", rank);


    // end
	pvm_lvgroup("tasks");
	pvm_exit();
}
